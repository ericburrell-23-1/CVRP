import math
import time
import xpress as xp
from networkx import DiGraph, shortest_path, path_weight
from numpy import array
from models.data_structures.customer import Customer
from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model, convert_to_ILP
from data.read_problem_data import generate_problem
from debug.col_gen import check_route_reduced_cost_with_RCI, check_rc_from_matrix
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, LA_Arc
from utilities.compute_beta import compute_beta, create_LA_arc_graph, node_sort
from utilities.model_updates.update_easy_edge_PGM import update_model, add_family_to_model, add_RCI_constrs
from utilities.RCI.identify_violated_inequalities import identify_violated_ineqs, RCI_preprocessing

MY_DIVISOR = 2
epsilon = 0.00001


def consistent_N2_arcs(omega_y_l: list, N2_pairs: list, incumbent_arcs: list):
    """
    Given `omega_y_l` being the full list (items corresponding to each route family) of dictionaries (keyed by y) of LA-Arcs, returns a list containing the subsets of the original that are compliant with the pairs in the corresponding set in `N2_pairs`. Also returns the list of new arcs that were added this iteration, unless `incumbent_arcs` is an empty list.
    """
    consistent_arcs = []
    new_arcs = []
    for l, omega_y in enumerate(omega_y_l):
        consistent_arcs.append(dict())
        new_arcs.append(dict())
        for (u_p, v_p, d) in omega_y:
            if (u_p, v_p) in N2_pairs[l]:
                consistent_arcs[l][(u_p, v_p, d)] = omega_y[(u_p, v_p, d)]
                if len(incumbent_arcs) <= l or (u_p, v_p, d) not in incumbent_arcs[l]:
                    new_arcs[l][(u_p, v_p, d)] = omega_y[(u_p, v_p, d)]

    if len(incumbent_arcs) == 0:
        return consistent_arcs
    
    return consistent_arcs, new_arcs
        



def consistent_N2_graphs(omega_R_plus: list, N2_pairs: list, incumbent_graphs: list):
    """
    Given the list of graphs `omega_R_plus` of the form (edges, nodes), returns the subsets of edges and nodes that are compliant with the corresponding set of pairs in `N2_pairs`. Also returns the list of new graph edges that were added this iteration, unless `incumbent_graphs` is an empty list.
    """
    consistent_graphs = []
    new_edges = []
    for l, (edges, _) in enumerate(omega_R_plus):
        consistent_edges = set()
        consistent_nodes = set()
        new_edges.append(set())
        for (i, j) in edges:
            if (i.u.id, j.u.id) in N2_pairs[l]:
                consistent_nodes.add(i)
                consistent_nodes.add(j)
                consistent_edges.add((i, j))
                
                if len(incumbent_graphs) <= l or (i, j) not in incumbent_graphs[l][0]:
                    new_edges[l].add((i, j))

        sorted_nodes = sorted(consistent_nodes, key=node_sort)
        consistent_graphs.append((consistent_edges, sorted_nodes))


    if len(incumbent_graphs) == 0:
        return consistent_graphs
    
    return consistent_graphs, new_edges


def arc_reduced_cost(arc: LA_Arc, cover_constraints: dict, RCI_constrs: dict, model: xp.problem):
    """Helper function to compute reduced cost of an LA-Arc"""
    rc = arc.cost
    for (idx, u) in enumerate(arc.visits[:-1]):
        rc -= model.getDual(cover_constraints[u.id])


        v = arc.visits[idx + 1]
        if RCI_constrs != {}:
            RCIs = RCI_constrs[u.id] - RCI_constrs[v.id]
        else:
            RCIs = set()

        for c in RCIs:
            dual = model.getDual(c[0])
            # print(dual)
            rc -= dual

    return rc


def lowest_rc_route_in_family(route_family: tuple, omega_y: dict, cover_constraints: dict, RCI_constrs: dict, model: xp.problem):
    """
    For a given `route_family` in the tuple (edges, nodes) and dictionary `omega_y` of LA-Arcs (keyed by y), returns pairs of customers (u_p, v_p) associated with arcs in the lowest cost route in the family.
    """
    rc_arc = {}
    rc_edge = {}
    # GET REDUCED COST OF EACH ARC
    for y in omega_y:
        for arc in omega_y[y]:
            rc_arc[arc.id] = arc_reduced_cost(arc, cover_constraints, RCI_constrs, model)

    # FIND REDUCED COST FOR EACH EDGE IN GRAPH BASED ON LOWEST REDUCED COST ARC
    start_node = route_family[1][0]
    for (i, j) in route_family[0]:
        if i.u.id == start_node.u.id:
            i_id = "Source"
        else:
            i_id = i.name
        if j.u.id == "end":
            j_id = "Sink"
        else:
            j_id = j.name

        if i_id == "Source":
            rc_edge[(i_id, j_id)] = math.hypot(i.u.x - j.u.x, i.u.y - j.u.y)
        else:
            d = int(round(i.cap_remain - j.cap_remain))
            for arc in omega_y.get((i.u.id, j.u.id, d), []):
                if (i_id, j_id) not in rc_edge:
                    rc_edge[(i_id, j_id)] = rc_arc[arc.id]
                elif rc_arc[arc.id] < rc_edge[(i_id, j_id)]:
                    rc_edge[(i_id, j_id)] = rc_arc[arc.id]

    # PRICE OVER GRAPH WITH EDGE WEIGHTS IN RC_EDGE
    g = DiGraph(directed=True)
    for (i_id, j_id) in rc_edge:
        g.add_edge(i_id, j_id, weight=rc_edge[(i_id, j_id)])


    path = shortest_path(g, "Source", "Sink", "weight", 'bellman-ford')
    rc = path_weight(g, path, "weight")

    path_customers = []
    for node_name in path[1:-1]:
        path_customers.append(node_name.split('_')[0])

    # print(f"Found path {path} with rc = {round(rc, 4)}")

    return path_customers, rc


def PGM_last_graph(DATA_SET, NUM_LA_NEIGHBORS):
    customers, start_depot, end_depot, capacity = generate_problem(DATA_SET, MY_DIVISOR, NUM_LA_NEIGHBORS)

    customers_by_id = {}
    for u in customers + [start_depot, end_depot]:
        customers_by_id[u.id] = u

    initial_N2_pairs = set()
    for c in customers:
        initial_N2_pairs.add((start_depot.id, c.id))
        initial_N2_pairs.add((c.id, end_depot.id))

    N2_pairs = [set()]
    N2_pairs[0].update(initial_N2_pairs)

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]
    omega_y = find_LA_arcs(customers, end_depot, capacity)
    omega_y_l = []
    omega_R_plus = []

    RCI_data = RCI_preprocessing(customers, start_depot, end_depot, capacity)
    RCI_constrs = {}
    for c in customers + [end_depot, start_depot]:
        RCI_constrs[c.id] = set()

    for route in omega_r:
        beta = compute_beta(route, customers)
        omega_y_l.append(compute_omega_y_l(beta, omega_y))
        (edges, nodes) = create_LA_arc_graph(omega_y_l[-1], beta, capacity)
        # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
        omega_R_plus.append((edges, nodes))


    N2_omega_y_l = consistent_N2_arcs(omega_y_l, N2_pairs, [])
    N2_omega_R_plus = consistent_N2_graphs(omega_R_plus, N2_pairs, [])

    start_time = time.time()
    model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)    


    pricing_time = 0
    column_gen_count = 0
    graph_manage_count = 0
    continue_iter = True
    while continue_iter:
        continue_inner_optimization = True
        while continue_inner_optimization:
            # OPTIMIZE NEW MODEL
            model.optimize()
            new_RCIs = identify_violated_ineqs(model, x_ij, RCI_data, customers, end_depot)
            add_RCI_constrs(model, new_RCIs, RCI_constrs)
            model.optimize()
            print(f"Model has an LP objective val = {model.getObjVal()}")

            # UPDATE N2 AND CONTINUE IF NEGATIVE RC PATH EXISTS
            continue_inner_optimization = False
            # for (l, _) in enumerate(omega_r):
            l = len(omega_r) - 1
            l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], omega_y_l[l], cover_constrs, RCI_constrs, model)
            graph_manage_count += 1
            if rc < -epsilon:
                continue_inner_optimization = True
                if len(l_hat_l) > 1:
                    for idx, c1 in enumerate(l_hat_l[:-1]):
                        c2 = l_hat_l[idx + 1]
                        N2_pairs[l].add((c1, c2))

            # UPDATE ARCS AND EDGES BASED ON NEW N2
            if continue_inner_optimization:
                # GET VIOLATED RCI INEQUALITIES
                # new_RCIs = identify_violated_ineqs(model, x_p, N2_omega_y_l, customers, end_depot, capacity, RCI_subsets)

                # UPDATE GRAPH AND ARC SETS
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)

                # MAKE CHANGES TO MODEL
                update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)


        # COLUMN GEN WHEN INNER OPTIMIZATION FINISHED
        pricing_start = time.time()
        new_route, new_rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity, RCI_constrs)
        # check_route_reduced_cost_with_RCI(model, RCI_constrs, cover_constrs, customers, start_depot, end_depot, new_route)
        # check_rc_from_matrix(model, new_route, x_ij, capacity)
        pricing_time += (time.time() - pricing_start)


        if new_rc >= -epsilon:
            print(
                f"Done solving. Non-negative reduced cost: rc = {round(new_rc, 4)}\n")
            continue_iter = False
        else:
            column_gen_count += 1
            print(f"New path has rc = {round(new_rc, 4)}")
            omega_r.append(new_route)
            beta = compute_beta(new_route, customers)
            omega_y_l.append(compute_omega_y_l(beta, omega_y))
            omega_R_plus.append(create_LA_arc_graph(
                omega_y_l[-1], beta, capacity))
            N2_pairs.append(set())
            N2_pairs[-1].update(initial_N2_pairs)

            N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
            N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)

            add_family_to_model(model, N2_omega_R_plus, N2_omega_y_l, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
            
    end_LP_time = time.time()
    convert_to_ILP(model)
    model.controls.outputlog = 1
    model.optimize()
    end_time = time.time()

    print(f"Finished solving entire problem in {round(end_time - start_time, 1)} seconds.\nLP time was {round(end_LP_time - start_time, 1)}.\nRan column gen {column_gen_count} times.\nCalled graph management {graph_manage_count} times for the last graph.\nSpent {round(pricing_time, 1)} seconds pricing.")
            

            






    




    