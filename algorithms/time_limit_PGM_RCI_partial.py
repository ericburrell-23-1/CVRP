import time
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, LA_Arc
from utilities.compute_beta import compute_beta, create_LA_arc_graph, node_sort
from utilities.model_updates.update_easy_edge_PGM import update_model, add_family_to_model, add_RCI_constrs
from utilities.RCI.identify_violated_inequalities import identify_violated_ineqs, RCI_preprocessing
from utilities.partial_pricing import partial_pricing_PGM
from utilities.PGM.PGM import consistent_N2_arcs, consistent_N2_graphs, add_RCI_to_uv_matrix, PGM
from utilities.partial_pricing import add_complimentary_column_edges
from utilities.PGM.algorithm_functions import problem_setup_PP
from models.lp_models.RMP_GM_LA import convert_to_ILP
from data.print_results import write_test_data_to_file



def TL_PGM_PP_with_RCI(DATA_SET: str, LA_COUNT: int, TIME_LIMIT: int = 30):
    # SETUP PROBLEM AND PREPROCESS
    start_time = time.time()
    print("Preprocessing.")
    customers, start_depot, end_depot, capacity, RCI_data, RCI_constrs, initial_N2_pairs, N2_pairs, N2_omega_y_l, N2_omega_R_plus, omega_r, omega_y, omega_y_l, omega_R_plus, model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p, arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows, uv_matrix, cost_vector, all_dual_constrs, first_beta = problem_setup_PP(DATA_SET, LA_COUNT)
    print("Preprocessing complete.")

    # INITIALIZE ALL TIMING/PERFORMANCE CODE
    preprocess_time = time.time() - start_time
    pricing_count = 0
    total_graph_manage_calls = 0
    successful_graph_manage_calls = 0
    graph_manage_count = 0
    comp_col_time = 0
    PGM_model_update_time = 0
    LP_solve_time = 0
    check_RCI_time = 0
    add_RCI_to_model_time = 0
    add_RCI_to_PGM_time = 0
    PGM_time = 0
    PGM_update_N2_time = 0
    pricing_time = 0
    build_new_graph_time = 0

    # SOLVE ONCE AND ADD MANY EDGES VIA COMPLIMENTARY COLUMN PRICING OPERATION
    print("Solving LP first Iteration")
    start_operation = time.time()
    model.optimize()
    LP_solve_time += time.time() - start_operation
    print(f"Finished solving. Objective = {model.getObjVal()}")

    start_operation = time.time()
    add_complimentary_column_edges(model, first_beta, cover_constrs, customers, start_depot, end_depot, capacity, omega_r, omega_R_plus, omega_y_l, omega_y, N2_pairs)
    comp_col_time += time.time() - start_operation

    start_operation = time.time()
    N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
    N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
    PGM_update_N2_time += time.time() - start_operation

    start_operation = time.time()
    update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
    PGM_model_update_time += time.time() - start_operation

    # OPTIMIZATION LOOP
    continue_GM = True
    while continue_GM:
        if time.time() - start_time - preprocess_time > TIME_LIMIT:
            break
        # INNER OPTIMIZATION LOOP (PGM)
        continue_PGM = True
        while continue_PGM:
            if time.time() - start_time - preprocess_time > TIME_LIMIT:
                break
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

            if time.time() - start_time - preprocess_time > TIME_LIMIT:
                break
            # PGM USING MOST RECENT SOLUTION
            start_operation = time.time()
            continue_PGM, gm_calls, successful_gm_calls = PGM(omega_r, omega_R_plus, y_arc_rows, all_dual_constrs, uv_matrix, cost_vector, arc_matrix, model, N2_pairs)
            PGM_time += time.time() - start_operation
            # RECORD PGM CALL COUNTS
            graph_manage_count += 1
            total_graph_manage_calls += gm_calls
            successful_graph_manage_calls += successful_gm_calls

            if continue_PGM:
                if len(omega_r) == 1:
                    start_operation = time.time()
                    add_complimentary_column_edges(model, first_beta, cover_constrs, customers, start_depot, end_depot, capacity, omega_r, omega_R_plus, omega_y_l, omega_y, N2_pairs)
                    comp_col_time += time.time() - start_operation

                    # start_operation = time.time()
                    # N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                    # N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
                    # PGM_update_N2_time += time.time() - start_operation

                    # start_operation = time.time()
                    # update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
                    # PGM_model_update_time += time.time() - start_operation

                # UPDATE GRAPH AND ARC SETS
                start_operation = time.time()
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
                PGM_update_N2_time += time.time() - start_operation

                # MAKE CHANGES TO MODEL
                start_operation = time.time()
                update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
                PGM_model_update_time += time.time() - start_operation

        if time.time() - start_time - preprocess_time > TIME_LIMIT:
                break
        
        # PARTIAL PRICING TO QUICKLY GET NEW GRAPH
        print("Doing partial pricing")
        start_operation = time.time()
        pricing_time_limit = TIME_LIMIT - (time.time() - start_time) + preprocess_time
        continue_GM, beta = partial_pricing_PGM(model, cover_constrs, customers, start_depot, end_depot, capacity, omega_r, omega_R_plus, omega_y_l, omega_y, N2_pairs, RCI_constrs, pricing_time_limit)
        pricing_time += time.time() - start_operation
        pricing_count += 1

        if continue_GM:
            print(f"LP obj = {round(model.getObjVal(), 2)}")
            start_operation = time.time()
            N2_pairs[-1].update(initial_N2_pairs)
            N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
            PGM_update_N2_time = time.time() - start_operation
            start_operation = time.time()
            omega_R_plus.append(create_LA_arc_graph(omega_y_l[-1], beta, capacity))
            build_new_graph_time += time.time() - start_operation
            start_operation = time.time()
            N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
            PGM_update_N2_time += time.time() - start_operation

            start_operation = time.time()
            add_family_to_model(model, N2_omega_R_plus, N2_omega_y_l, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
            PGM_model_update_time += time.time() - start_operation
        else:
            print("Done iterating. Solving ILP.")

    start_operation = time.time()
    model.optimize()
    LP_solve_time += time.time() - start_operation
    LP_obj_val = model.getObjVal()
    end_LP_time = time.time()
    convert_to_ILP(model)
    model.controls.outputlog = 1
    model.controls.maxtime = 15
    model.optimize()
    end_time = time.time()
    ILP_obj_val = model.getObjVal()

    iteration_time = end_LP_time - start_time - preprocess_time
    total_time = end_time - start_time - preprocess_time
    total_time_plus_preprocess = total_time + preprocess_time
    ILP_solve_time = end_LP_time - end_time
    real_time = LP_solve_time + ILP_solve_time


    results = {
        "Algorithm": "Small-Capacity PGM", 
        "Data_set": DATA_SET,
        "LA_count": LA_COUNT,
        "Time_limit": TIME_LIMIT,
        "Preprocessing_time": round(preprocess_time, 2),
        "Pricing_count": pricing_count,
        "Total_graph_manage_calls": total_graph_manage_calls,
        "Successful_graph_manage_calls": successful_graph_manage_calls,
        "Graph_manage_count": graph_manage_count,
        "Comp_col_time": round(comp_col_time, 2),
        "PGM_model_update_time": round(PGM_model_update_time, 2),
        "LP_solve_time": round(LP_solve_time, 2),
        "Check_RCI_time": round(check_RCI_time, 2),
        "Add_RCI_to_model_time": round(add_RCI_to_model_time, 2),
        "Add_RCI_to_PGM_time": round(add_RCI_to_PGM_time, 2),
        "PGM_time": round(PGM_time, 2),
        "PGM_update_N2_time": round(PGM_update_N2_time, 2),
        "Pricing_time": round(pricing_time, 2),
        "Build_new_graph_time": round(build_new_graph_time, 2),
        "Iteration_time": round(iteration_time, 2),
        "Total_time": round(total_time, 2),
        "Total_time_plus_preprocess": round(total_time_plus_preprocess, 2),
        "LP_Objective_Val": round(LP_obj_val),
        "ILP_Objective_Val": round(ILP_obj_val),
        "ILP_solve_time": round(ILP_solve_time, 2),
        "Real_time": round(real_time, 2)
    }

    write_test_data_to_file(results, "Small_Cap_PGM.csv")



    print(f"Finished solving entire problem in {round(end_time - start_time - preprocess_time, 1)} seconds.\nLP time was {round(end_LP_time - start_time - preprocess_time, 1)}.\nRan column gen {pricing_count} times.\n{graph_manage_count} iterations of PGM with a total of {total_graph_manage_calls} calls to PGM.\n{successful_graph_manage_calls} of those calls found rc < 0.")
