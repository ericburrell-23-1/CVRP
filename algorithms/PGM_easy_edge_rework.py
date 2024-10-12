import time
from models.data_structures.customer import Customer
from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model, convert_to_ILP
from data.read_problem_data import generate_problem
# from debug.col_gen import check_route_reduced_cost_with_RCI, check_rc_from_matrix
from debug.RMP_GM_LA import show_primal
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, LA_Arc
from utilities.compute_beta import compute_beta, create_LA_arc_graph, node_sort
from utilities.model_updates.update_easy_edge_PGM import update_model, add_family_to_model, add_RCI_constrs
from utilities.RCI.identify_violated_inequalities import identify_violated_ineqs, RCI_preprocessing
from utilities.PGM.PGM import consistent_N2_arcs, consistent_N2_graphs, pgm_preprocessing, add_RCI_to_uv_matrix, PGM

MY_DIVISOR = 1
epsilon = 0.00001


def problem_setup(DATA_SET, NUM_LA_NEIGHBORS):
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

    return customers, start_depot, end_depot, capacity, RCI_data, RCI_constrs, initial_N2_pairs, N2_pairs, N2_omega_y_l, N2_omega_R_plus, omega_r, omega_y, omega_y_l, omega_R_plus, model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p, arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows, uv_matrix, cost_vector, all_dual_constrs


def add_new_graph(new_route, new_rc, omega_r, customers, omega_y_l, omega_y, omega_R_plus, N2_omega_y_l, N2_omega_R_plus, capacity, N2_pairs, initial_N2_pairs, model, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs):
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

    return N2_omega_y_l, new_arcs, N2_omega_R_plus, new_edges



def PGM_easy_edge(DATA_SET, NUM_LA_NEIGHBORS):
    start_time = time.time()
    customers, start_depot, end_depot, capacity, RCI_data, RCI_constrs, initial_N2_pairs, N2_pairs, N2_omega_y_l, N2_omega_R_plus, omega_r, omega_y, omega_y_l, omega_R_plus, model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p, arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows, uv_matrix, cost_vector, all_dual_constrs = problem_setup(DATA_SET, NUM_LA_NEIGHBORS)


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
            N2_omega_y_l, new_arcs, N2_omega_R_plus, new_edges = add_new_graph(new_route, new_rc, omega_r, customers, omega_y_l, omega_y, omega_R_plus, N2_omega_y_l, N2_omega_R_plus, capacity, N2_pairs, initial_N2_pairs, model, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
            
    end_LP_time = time.time()
    # show_primal(model, x_ij)
    convert_to_ILP(model)
    model.controls.outputlog = 1
    model.optimize()
    end_time = time.time()
    show_primal(model, x_ij)

    print(f"Finished solving entire problem in {round(end_time - start_time, 1)} seconds.\nLP time was {round(end_LP_time - start_time, 1)}.\nRan column gen {column_gen_count} times.\n{graph_manage_count} iterations of PGM with a total of {total_graph_manage_calls} calls to PGM.\n{successful_graph_manage_calls} of those calls found rc < 0.")
    # show_primal(model, x_ij)
            