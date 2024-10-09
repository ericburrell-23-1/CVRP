import math
import time
import xpress as xp
import scipy.sparse as sp
from networkx import DiGraph, shortest_path, path_weight
from numpy import array, zeros, ndarray
from models.data_structures.customer import Customer
from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model, convert_to_ILP
from data.read_problem_data import generate_problem
from debug.col_gen import check_route_reduced_cost_with_RCI, check_rc_from_matrix
from debug.RMP_GM_LA import show_primal
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
        RCIs = RCI_constrs[u.id] - RCI_constrs[v.id]
        for c in RCIs:
            dual = model.getDual(c[0])
            # print(dual)
            rc -= dual

    return rc


def add_RCI_to_uv_matrix(uv_matrix: sp.csr_matrix, all_constr: list, uv_row_indices: dict, RCI_added: list, customers: list, end_depot: Customer):
    uv_matrix_lil = uv_matrix.tolil()

    for (constr, N_hat) in RCI_added:
        uv_contrib = zeros((uv_matrix.shape[0],), dtype=int)
        all_constr.append(constr)
        for u in N_hat:
            for v in set((customers + [end_depot])) - set(N_hat):
                uv_contrib[uv_row_indices[u.id, v.id]] = 1

        uv_matrix_lil = sp.hstack([uv_matrix_lil, uv_contrib[:, None]])

    uv_matrix = uv_matrix_lil.tocsr()

    return uv_matrix




def pgm_uv_preprocessing(customers: list, end_depot: Customer, uv_col_indices: dict, cover_constraints: dict):
    cost_vector = zeros(len(uv_col_indices))
    all_dual_constrs = [] # PASS TO GETDUAL TO GET PROPER DUAL VALUES
    uv_contrib_indices = {}

    for u in customers:
        constr_idx = len(all_dual_constrs)
        all_dual_constrs.append(cover_constraints[u.id])
        for v in customers + [end_depot]:
            if u.id == v.id:
                continue
            cost = math.hypot(u.x - v.x, u.y - v.y)
            idx = uv_col_indices[u.id, v.id]
            cost_vector[idx] = cost
            uv_contrib_indices[idx] = constr_idx

    sparse_matrix = sp.lil_matrix((len(uv_col_indices), len(all_dual_constrs)), dtype=int)

    for row_idx in uv_contrib_indices:
        col_idx = uv_contrib_indices[row_idx]
        sparse_matrix[row_idx, col_idx] = 1

    uv_matrix = sparse_matrix.tocsr()

    PGM_uv_data = (uv_matrix, cost_vector, all_dual_constrs)

    return PGM_uv_data



def pgm_arc_preprocessing(omega_y: dict, customers: list, end_depot: Customer):
    uv_col_indices = {}
    arc_row_indices = {}
    y_arc_rows = {}
    arc_contrib_indices = {}

    col_idx = 0
    for u in customers:
        for v in customers + [end_depot]:
            if u.id == v.id:
                continue
            uv_col_indices[u.id, v.id] = col_idx
            col_idx += 1

    row_idx = 0
    for y in omega_y:
        y_start = row_idx
        for arc in omega_y[y]:
            arc_contrib_indices[row_idx] = []
            for u_id, v_id in arc.a_uvp:
                arc_contrib_indices[row_idx].append(uv_col_indices[u_id, v_id])
            arc_row_indices[arc.id] = row_idx
            row_idx += 1
        y_end = row_idx
        y_arc_rows[y] = (y_start, y_end)

    sparse_matrix = sp.lil_matrix((len(arc_row_indices), len(uv_col_indices)), dtype=int)

    for row_idx in arc_contrib_indices:
        for col_idx in arc_contrib_indices[row_idx]:
            sparse_matrix[row_idx, col_idx] = 1

    arc_matrix = sparse_matrix.tocsr()

    PGM_arc_data = (arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows)

    return PGM_arc_data



def pgm_preprocessing(omega_y: dict, customers: list, end_depot: Customer, cover_constrs: dict):
    PGM_arc_data = pgm_arc_preprocessing(omega_y, customers, end_depot)

    PGM_uv_data = pgm_uv_preprocessing(customers, end_depot, PGM_arc_data[2], cover_constrs)

    return PGM_arc_data, PGM_uv_data



def calculate_PGM_arc_weights(model: xp.problem, all_dual_constrs: list, uv_matrix: sp.csr_matrix, cost_vector: ndarray, arc_matrix: sp.csr_matrix):
    # GET THE DUAL VECTOR
    dual_vector = model.getDual(all_dual_constrs)

    # COMPUTE REDUCED_COST_UV VECTOR
    rc_uv_vector = cost_vector - uv_matrix.dot(dual_vector)

    # USE RC_UV VECTOR TO COMPUTE RC_ARC VECTOR
    rc_arc_vector = arc_matrix.dot(rc_uv_vector)

    return rc_arc_vector


def lowest_rc_route_in_family(route_family: tuple, y_arc_rows: dict, rc_arc_vector: ndarray):
    rc_edge = {}
    # GET REDUCED COST OF EACH ARC

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
            indices = y_arc_rows.get((i.u.id, j.u.id, d), None)
            if indices != None:
                start, stop = indices
                rc_edge[(i_id, j_id)] = min(rc_arc_vector[start:stop])



    # PRICE OVER GRAPH WITH EDGE WEIGHTS IN RC_EDGE
    g = DiGraph(directed=True)
    for (i_id, j_id) in rc_edge:
        g.add_edge(i_id, j_id, weight=rc_edge[(i_id, j_id)])

    path = shortest_path(g, "Source", "Sink", "weight", 'bellman-ford')
    rc = path_weight(g, path, "weight")

    path_customers = []
    for node_name in path[1:-1]:
        path_customers.append(node_name.split('_')[0])

    print(f"Found path {path} with rc = {round(rc, 4)}")

    return path_customers, rc


def PGM(omega_r, omega_R_plus, y_arc_rows: dict, all_dual_constrs: list, uv_matrix: sp.csr_matrix, cost_vector: ndarray, arc_matrix: sp.csr_matrix, model: xp.problem, N2_pairs: list):
    rc_arc_vector = calculate_PGM_arc_weights(model, all_dual_constrs, uv_matrix, cost_vector, arc_matrix)
    continue_inner_optimization = False
    gm_calls = 0
    successful_gm_calls = 0

    for (l, _) in enumerate(omega_r):
                gm_calls += 1
                start_solve = time.time()
                l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], y_arc_rows, rc_arc_vector)
                end_solve = time.time()
                # print(f"Spent {round(end_solve - start_solve, 3)} seconds solving in lowest_rc_route function.")
                if rc < -epsilon:
                    successful_gm_calls += 1
                    continue_inner_optimization = True
                    if len(l_hat_l) > 1:
                        for idx, c1 in enumerate(l_hat_l[:-1]):
                            c2 = l_hat_l[idx + 1]
                            N2_pairs[l].add((c1, c2))

    return continue_inner_optimization, gm_calls, successful_gm_calls



# def update_pgm_edges(graph: DiGraph, cover_constraints: dict, prev_cover_duals: dict, RCI_constraints: dict, prev_RCI_duals: dict, model: xp.problem):
#     for c in cover_constraints:
#         print("Get the duals and update the edges here")
#     for c in RCI_constraints:
#         print("Get the duals and update the edges here")

#     # Return the updated graph and also the edges that were changed so we can easily change them back



# def lowest_rc_route_in_family(graph: DiGraph, route_family: tuple, omega_y: dict, cover_constraints: dict, RCI_constrs: dict, model: xp.problem):
#     """
#     For a given `route_family` in the tuple (edges, nodes) and dictionary `omega_y` of LA-Arcs (keyed by y), returns pairs of customers (u_p, v_p) associated with arcs in the lowest cost route in the family.
#     """


#     start_solve = time.time()
#     path = shortest_path(graph, "Source", "Sink", "weight", 'bellman-ford')
#     rc = path_weight(graph, path, "weight")
#     end_solve = time.time()

#     print(f"Spent {round(end_solve - start_solve, 3)} seconds solving SPP.")

#     path_customers = []
#     for node_name in path[1:-1]:
#         path_customers.append(node_name.split('_')[0])

#     print(f"Found path {path} with rc = {round(rc, 4)}")

#     return path_customers, rc


def PGM_easy_edge(DATA_SET, NUM_LA_NEIGHBORS):
    start_time = time.time()
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

    model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)
    
    PGM_arc_data, PGM_uv_data = pgm_preprocessing(omega_y, customers, end_depot, cover_constrs)
    arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows = PGM_arc_data
    uv_matrix, cost_vector, all_dual_constrs = PGM_uv_data


    column_gen_count = 0
    total_graph_manage_calls = 0
    successful_graph_manage_calls = 0
    graph_manage_count = 0
    continue_iter = True
    while continue_iter:
        continue_inner_optimization = True
        pgm_time = 0
        while continue_inner_optimization:
            # OPTIMIZE NEW MODEL
            model.optimize()
            new_RCIs = identify_violated_ineqs(model, x_ij, RCI_data, customers, end_depot)
            if len(new_RCIs) > 0:
                RCI_added = add_RCI_constrs(model, new_RCIs, RCI_constrs)
                uv_matrix = add_RCI_to_uv_matrix(uv_matrix, all_dual_constrs, uv_col_indices, RCI_added, customers, end_depot)
            model.optimize()
            print(f"Model has an LP objective val = {model.getObjVal()}")

            # UPDATE N2 AND CONTINUE IF NEGATIVE RC PATH EXISTS
            start_pgm = time.time()
            continue_inner_optimization, gm_calls, successful_gm_calls = PGM(omega_r, omega_R_plus, y_arc_rows, all_dual_constrs, uv_matrix, cost_vector, arc_matrix, model, N2_pairs)
            pgm_time += (time.time() - start_pgm)
            # print(f"PGM for all graphs took {round(end_pgm - start_pgm, 2)} seconds.")
            graph_manage_count += 1
            total_graph_manage_calls += gm_calls
            successful_graph_manage_calls += successful_gm_calls

            # UPDATE ARCS AND EDGES BASED ON NEW N2
            if continue_inner_optimization:
                # GET VIOLATED RCI INEQUALITIES
                # new_RCIs = identify_violated_ineqs(model, x_p, N2_omega_y_l, customers, end_depot, capacity, RCI_subsets)

                # UPDATE GRAPH AND ARC SETS
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)

                # MAKE CHANGES TO MODEL
                update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)

        print(f"PGM took {round(pgm_time, 2)} seconds total")

        # COLUMN GEN WHEN INNER OPTIMIZATION FINISHED
        new_route, new_rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity, RCI_constrs)
        # check_route_reduced_cost_with_RCI(model, RCI_constrs, cover_constrs, customers, start_depot, end_depot, new_route)
        # check_rc_from_matrix(model, new_route, x_ij, capacity)

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
    # show_primal(model, x_ij)
    convert_to_ILP(model)
    model.controls.outputlog = 1
    model.optimize()
    end_time = time.time()

    print(f"Finished solving entire problem in {round(end_time - start_time, 1)} seconds.\nLP time was {round(end_LP_time - start_time, 1)}.\nRan column gen {column_gen_count} times.\n{graph_manage_count} iterations of PGM with a total of {total_graph_manage_calls} calls to PGM.\n{successful_graph_manage_calls} of those calls found rc < 0.")
    # show_primal(model, x_ij)
            