import math
import xpress as xp
from networkx import DiGraph, shortest_path, path_weight
from numpy import array
from models.data_structures.customer import Customer
from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, LA_Arc
from utilities.compute_beta import compute_beta, create_LA_arc_graph, node_sort
MY_DIVISOR = 20
epsilon = 0.00001


def consistent_N2_arcs(omega_y_l: list, N2_pairs: set):
    """
    Given `omega_y_l` being the full list (items corresponding to each route family) of dictionaries (keyed by y) of LA-Arcs, returns a list containing the subsets of the original that are compliant with the pairs in the set `N2_pairs`.
    """
    consistent_arcs = []
    for l, omega_y in enumerate(omega_y_l):
        consistent_arcs.append(dict())
        for (u_p, v_p, d) in omega_y:
            if (u_p, v_p) in N2_pairs:
                consistent_arcs[l][(u_p, v_p, d)] = omega_y[(u_p, v_p, d)]

    return consistent_arcs


def consistent_N2_graphs(omega_R_plus, N2_pairs):
    """
    Given the list of graphs `omega_R_plus` of the form (edges, nodes), returns the subsets of edges and nodes that are compliant with the set of pairs `N2_pairs`.
    """
    consistent_graphs = []
    for (edges, _) in omega_R_plus:
        consistent_edges = set()
        consistent_nodes = set()
        for (i, j) in edges:
            if (i.u.id, j.u.id) in N2_pairs:
                consistent_nodes.add(i)
                consistent_nodes.add(j)
                consistent_edges.add((i, j))

        sorted_nodes = sorted(consistent_nodes, key=node_sort)
        consistent_graphs.append((consistent_edges, sorted_nodes))

    return consistent_graphs


def arc_reduced_cost(arc: LA_Arc, cover_constraints: dict, model: xp.problem):
    """Helper function to compute reduced cost of an LA-Arc"""
    rc = arc.cost
    for c in arc.visits[:-1]:
        rc -= model.getDual(cover_constraints[c.id])

    return rc


def lowest_rc_route_in_family(route_family: tuple, omega_y: dict, cover_constraints: dict, model: xp.problem):
    """
    For a given `route_family` in the tuple (edges, nodes) and dictionary `omega_y` of LA-Arcs (keyed by y), returns pairs of customers (u_p, v_p) associated with arcs in the lowest cost route in the family.
    """
    rc_arc = {}
    rc_edge = {}
    # GET REDUCED COST OF EACH ARC
    for y in omega_y:
        for arc in omega_y[y]:
            rc_arc[arc.id] = arc_reduced_cost(arc, cover_constraints, model)

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

    print(f"Found path {path} with rc = {rc}")

    return path_customers, rc


def PGM_easy_edge(DATA_SET, NUM_LA_NEIGHBORS):
    customers, start_depot, end_depot, capacity = generate_problem(DATA_SET, MY_DIVISOR, NUM_LA_NEIGHBORS)

    customers_by_id = {}
    for u in customers + [start_depot, end_depot]:
        customers_by_id[u.id] = u

    N2_pairs = set()
    for c in customers:
        N2_pairs.add((start_depot.id, c.id))
        N2_pairs.add((c.id, end_depot.id))

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]
    omega_y = find_LA_arcs(customers, end_depot, capacity)
    omega_y_l = []
    omega_R_plus = []

    for route in omega_r:
        beta = compute_beta(route, customers)
        omega_y_l.append(compute_omega_y_l(beta, omega_y))
        (edges, nodes) = create_LA_arc_graph(omega_y_l[-1], beta, capacity)
        # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
        omega_R_plus.append((edges, nodes))


    continue_iter = True
    while continue_iter:
        continue_inner_optimization = True
        while continue_inner_optimization:
            # UPDATE ARCS AND EDGES BASED ON NEW N2
            N2_omega_y_l = consistent_N2_arcs(omega_y_l, N2_pairs)
            N2_omega_R_plus = consistent_N2_graphs(omega_R_plus, N2_pairs)

            # OPTIMIZE NEW MODEL
            model, cover_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)    
            model.optimize()
            print(f"Model has an LP objective val = {model.getObjVal()}")

            # UPDATE N2 AND CONTINUE IF NEGATIVE RC PATH EXISTS
            continue_inner_optimization = False
            for (l, _) in enumerate(omega_r):
                l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], omega_y_l[l], cover_constrs, model)
                if rc < -epsilon:
                    continue_inner_optimization = True
                    if len(l_hat_l) > 1:
                        for idx, c1 in enumerate(l_hat_l[:-1]):
                            c2 = l_hat_l[idx + 1]
                            N2_pairs.add((c1, c2))

        # COLUMN GEN WHEN INNER OPTIMIZATION FINISHED
        new_route, new_rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity)
        
        if new_rc >= -epsilon:
            print(
                f"Done solving. Non-negative reduced cost: rc = {round(new_rc, 4)}\n")
            continue_iter = False
        else:
            print(f"New path has rc = {round(new_rc, 4)}")
            omega_r.append(new_route)
            beta = compute_beta(new_route, customers)
            omega_y_l.append(compute_omega_y_l(beta, omega_y))
            omega_R_plus.append(create_LA_arc_graph(
                omega_y_l[-1], beta, capacity))
            
    model.controls.outputlog = 1
    model.optimize()
            

            






    




    