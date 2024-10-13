import time
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, LA_Arc
from utilities.compute_beta import compute_beta, create_LA_arc_graph, node_sort
from utilities.model_updates.update_easy_edge_PGM import add_family_to_model, add_RCI_constrs
from utilities.model_updates.update_PGM_disc import update_model
from utilities.RCI.identify_violated_inequalities import identify_violated_ineqs, RCI_preprocessing
from utilities.PGM.PGM import add_RCI_to_uv_matrix
from utilities.PGM.shared_N2_discrete import consistent_N2_arcs, consistent_N2_graphs, PGM, augment_graphs
from utilities.partial_pricing import add_complimentary_column_edges_disc, partial_pricing_PGM_disc
from utilities.PGM.algorithm_functions import problem_setup_PP_disc
from models.lp_models.RMP_GM_LA import convert_to_ILP



def TL_PGM_PP_with_RCI(DATA_SET: str, LA_COUNT: int, TIME_LIMIT: int = 30):
    # SETUP PROBLEM AND PREPROCESS
    start_time = time.time()
    print("Preprocessing.")
    customers, customers_by_id, start_depot, end_depot, capacity, RCI_data, RCI_constrs, initial_N2_pairs, N2_pairs, N2_omega_y_l, N2_omega_R_plus, omega_r, omega_y, omega_y_l, omega_R_plus, model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p, arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows, uv_matrix, cost_vector, all_dual_constrs, betas = problem_setup_PP_disc(DATA_SET, LA_COUNT)
    print("Preprocessing complete.")

    # INITIALIZE ALL TIMING/PERFORMANCE CODE
    preprocess_time = time.time() - start_time
    pricing_count = 0
    total_graph_manage_calls = 0
    successful_graph_manage_calls = 0
    graph_manage_count = 0
    comp_col_time = 0
    edge_add_time = 0
    PGM_model_update_time = 0
    LP_solve_time = 0
    check_RCI_time = 0
    add_RCI_to_model_time = 0
    add_RCI_to_PGM_time = 0
    PGM_time = 0
    PGM_update_N2_time = 0
    pricing_time = 0

    # SOLVE ONCE AND ADD MANY EDGES VIA COMPLIMENTARY COLUMN PRICING OPERATION
    print("Solving LP first Iteration")
    start_operation = time.time()
    model.optimize()
    LP_solve_time += time.time() - start_operation
    print(f"Finished solving. Objective = {model.getObjVal()}")

    start_operation = time.time()
    new_N2 = add_complimentary_column_edges_disc(model, betas[0], cover_constrs, customers, start_depot, end_depot, capacity, omega_r, omega_R_plus, omega_y_l, omega_y, N2_pairs)
    comp_col_time += time.time() - start_operation

    start_operation = time.time()
    N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
    PGM_update_N2_time += time.time() - start_operation

    start_operation = time.time()
    augment_graphs(new_N2, omega_R_plus, N2_omega_y_l, new_arcs, betas, customers_by_id)
    edge_add_time += time.time() - start_operation

    start_operation = time.time()
    N2_omega_R_plus, new_edges, new_nodes = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
    PGM_update_N2_time += time.time() - start_operation

    start_operation = time.time()
    update_model(model, new_arcs, new_edges, new_nodes, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
    PGM_model_update_time += time.time() - start_operation

    # OPTIMIZATION LOOP
    continue_GM = True
    while continue_GM:
        if time.time() - start_time - preprocess_time > TIME_LIMIT:
            break
        # INNER OPTIMIZATION LOOP (PGM)
        continue_PGM = True
        while continue_PGM:
            # OPTIMIZE
            start_operation = time.time()
            model.optimize()
            LP_solve_time += time.time() - start_operation

            # CHECK FOR/ADD RCI
            start_operation = time.time()
            new_RCIs = identify_violated_ineqs(model, x_ij, RCI_data, customers, end_depot)
            check_RCI_time += time.time() - start_operation
            if len(new_RCIs) > 0:
                start_operation = time.time()
                RCI_added = add_RCI_constrs(model, new_RCIs, RCI_constrs)
                add_RCI_to_model_time += time.time() - start_operation

                start_operation = time.time()
                uv_matrix = add_RCI_to_uv_matrix(uv_matrix, all_dual_constrs, uv_col_indices, RCI_added, customers, end_depot)
                add_RCI_to_PGM_time += time.time() - start_operation

                start_operation = time.time()
                model.optimize()
                LP_solve_time += time.time() - start_operation

            # PGM USING MOST RECENT SOLUTION
            start_operation = time.time()
            continue_PGM, new_N2, gm_calls, successful_gm_calls = PGM(omega_r, omega_R_plus, y_arc_rows, all_dual_constrs, uv_matrix, cost_vector, arc_matrix, model, N2_pairs)
            PGM_time += time.time() - start_operation
            # RECORD PGM CALL COUNTS
            graph_manage_count += 1
            total_graph_manage_calls += gm_calls
            successful_graph_manage_calls += successful_gm_calls

            if continue_PGM:
                # UPDATE GRAPH AND ARC SETS
                start_operation = time.time()
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                PGM_update_N2_time += time.time() - start_operation
                
                start_operation = time.time()
                augment_graphs(new_N2, omega_R_plus, N2_omega_y_l, new_arcs, betas, customers_by_id)
                edge_add_time += time.time() - start_operation

                start_operation = time.time()
                N2_omega_R_plus, new_edges, new_nodes = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
                PGM_update_N2_time += time.time() - start_operation

                # MAKE CHANGES TO MODEL
                start_operation = time.time()
                update_model(model, new_arcs, new_edges, new_nodes, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
                PGM_model_update_time += time.time() - start_operation

        # PARTIAL PRICING TO QUICKLY GET NEW GRAPH
        print("Doing partial pricing")
        start_operation = time.time()
        pricing_time_limit = TIME_LIMIT - (time.time() - start_time) + preprocess_time
        continue_GM, beta, new_N2 = partial_pricing_PGM_disc(model, cover_constrs, customers, start_depot, end_depot, capacity, omega_r, omega_R_plus, omega_y_l, omega_y, N2_pairs, RCI_constrs, pricing_time_limit)
        betas.append(beta)
        pricing_time += time.time() - start_operation
        pricing_count += 1

        if continue_GM:
            print(f"LP obj = {round(model.getObjVal(), 2)}")
            omega_R_plus.append(create_LA_arc_graph(N2_omega_y_l[-1], beta, capacity))
            start_operation = time.time()

            N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
            PGM_update_N2_time += time.time() - start_operation

            start_operation = time.time()
            augment_graphs(new_N2, omega_R_plus[:-1], N2_omega_y_l[:-1], new_arcs[:-1], betas[:-1], customers_by_id)
            edge_add_time += time.time() - start_operation

            start_operation = time.time()
            N2_omega_R_plus, new_edges, new_nodes = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
            PGM_update_N2_time += time.time() - start_operation

            start_operation = time.time()
            update_model(model, new_arcs[:-1], new_edges[:-1], new_nodes[:-1], cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
            PGM_model_update_time += time.time() - start_operation

            start_operation = time.time()
            add_family_to_model(model, N2_omega_R_plus, N2_omega_y_l, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
            PGM_model_update_time += time.time() - start_operation
        else:
            print("Done iterating. Solving ILP.")

    end_LP_time = time.time()
    convert_to_ILP(model)
    model.controls.outputlog = 1
    model.controls.maxtime = 15
    model.optimize()
    end_time = time.time()

    print(f"Finished solving entire problem in {round(end_time - start_time - preprocess_time, 1)} seconds.\nLP time was {round(end_LP_time - start_time - preprocess_time, 1)}.\nRan column gen {pricing_count} times.\n{graph_manage_count} iterations of PGM with a total of {total_graph_manage_calls} calls to PGM.\n{successful_graph_manage_calls} of those calls found rc < 0.")
