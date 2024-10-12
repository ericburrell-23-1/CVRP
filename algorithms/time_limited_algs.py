import time
import math
import multiprocessing
import xpress as xp
from data.read_problem_data import generate_problem
from data.print_results import write_test_data_to_file
from algorithms.obsolete.PGM_last_graph import lowest_rc_route_in_family, consistent_N2_arcs, consistent_N2_graphs
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, LA_Arc
from utilities.compute_beta import compute_beta, create_LA_arc_graph, node_sort
from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model, convert_to_ILP
from utilities.model_updates.update_easy_edge_PGM import update_model, add_family_to_model, add_RCI_constrs
from utilities.RCI.identify_violated_inequalities import identify_violated_ineqs, RCI_preprocessing
from models.lp_models.RMP import create_RMP_model
from utilities.model_updates.update_CG import add_col_to_model
from utilities.partial_pricing import partial_pricing

MY_DIVISOR = 2
epsilon = 0.00001
time_limit = 30

def PGM_last_graph(DATA_SET, NUM_LA_NEIGHBORS):
    start_preprocess = time.time()
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

    pricing_time = 0
    pgm_time = 0
    lp_solve_time = 0
    model_update_time = 0
    extra_pricing_time = 0
    rci_count = 0
    start_time = time.time()
    model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)    


    column_gen_count = 0
    graph_manage_count = 0
    continue_iter = True
    while continue_iter:
        continue_inner_optimization = True
        while continue_inner_optimization:
            # OPTIMIZE NEW MODEL
            start_op = time.time()
            model.optimize()
            lp_solve_time += time.time() - start_op
            new_RCIs = identify_violated_ineqs(model, x_ij, RCI_data, customers, end_depot)
            if len(new_RCIs) != 0:
                rci_count += len(new_RCIs)
                start_op = time.time()
                add_RCI_constrs(model, new_RCIs, RCI_constrs)
                model_update_time += time.time() - start_op
                start_op = time.time()
                model.optimize()
                lp_solve_time += time.time() - start_op
            lp_val = model.getObjVal()
            print(f"Model has an LP objective val = {lp_val}")

            # UPDATE N2 AND CONTINUE IF NEGATIVE RC PATH EXISTS
            continue_inner_optimization = False
            # for (l, _) in enumerate(omega_r):
            l = len(omega_r) - 1

            start_op = time.time()
            l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], omega_y_l[l], cover_constrs, RCI_constrs, model)
            graph_manage_count += 1
            if rc < -epsilon:
                continue_inner_optimization = True
                if len(l_hat_l) > 1:
                    for idx, c1 in enumerate(l_hat_l[:-1]):
                        c2 = l_hat_l[idx + 1]
                        N2_pairs[l].add((c1, c2))

            if (time.time() - start_time) > time_limit:
                continue_inner_optimization = False
                continue_iter = False
                print("Terminating Inner Optimization")

            # UPDATE ARCS AND EDGES BASED ON NEW N2
            if continue_inner_optimization:
                # GET VIOLATED RCI INEQUALITIES
                # new_RCIs = identify_violated_ineqs(model, x_p, N2_omega_y_l, customers, end_depot, capacity, RCI_subsets)

                # UPDATE GRAPH AND ARC SETS
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
                pgm_time += time.time() - start_op

                # MAKE CHANGES TO MODEL
                start_op = time.time()
                update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
                model_update_time += time.time() - start_op
            else:
                pgm_time += time.time() - start_op

        time_before_CG = time.time()
        if (time.time() - start_time) > time_limit:
            print("Breaking out of loop before CG")
            break
        # COLUMN GEN WHEN INNER OPTIMIZATION FINISHED
        start_op = time.time()
        new_route, new_rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity, RCI_constrs)
        # check_route_reduced_cost_with_RCI(model, RCI_constrs, cover_constrs, customers, start_depot, end_depot, new_route)
        # check_rc_from_matrix(model, new_route, x_ij, capacity)

        if (time.time() - start_time) > time_limit:
            print(f"Breaking out of loop after CG. Time before CG was {round(time_before_CG - start_time, 1)}. Time at break is {round(time.time() - start_time, 1)}")
            extra_pricing_time = time.time() - time_before_CG
            break
        pricing_time += time.time() - start_op

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
            
            start_op = time.time()
            N2_pairs.append(set())
            N2_pairs[-1].update(initial_N2_pairs)

            N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
            N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
            pgm_time += time.time() - start_op

            start_op = time.time()
            add_family_to_model(model, N2_omega_R_plus, N2_omega_y_l, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
            model_update_time += time.time() - start_op

            
    end_LP_time = time.time()
    model.optimize()
    print(f"Finished solving LP in {round(end_LP_time - start_time, 1)} seconds.\nRan column gen {column_gen_count} times.\nCalled graph management {graph_manage_count} times for the last graph.")
    convert_to_ILP(model)
    model.controls.outputlog = 1
    start_op = time.time()
    model.optimize()
    end_time = time.time()
    ILP_solve_time = end_time - start_op
    ILP_val = model.getObjVal()

    print(f"Finished solving ILP in {round(end_time - start_time, 1)} seconds.")

    results = {
        "Algorithm": "Time-Limited Last-Graph PGM with RCI",
        "Data_set": DATA_SET,
        "Num_customers": len(customers),
        "Capacity_divisor": MY_DIVISOR,
        "Time_limit": time_limit,
        "LP_solve_time": round(lp_solve_time, 2),
        "ILP_solve_time": round(ILP_solve_time, 2),
        "PGM_time": round(pgm_time, 2),
        "Pricing_time": round(pricing_time, 2),
        "Preprocessing_time": round(start_time - start_preprocess, 2),
        "LP_obj_val": round(lp_val, 2),
        "ILP_obj_val": round(ILP_val, 2),
        "Total_time": round((end_time - start_time) - extra_pricing_time, 2),
        "CG_iterations": column_gen_count,
        "PGM_iterations": graph_manage_count,
        "RCI_constrs_added": rci_count
    }


    write_test_data_to_file(results, "time_limit_PGM_LG_RCI.csv")

            
def PGM_easy_edge(DATA_SET, NUM_LA_NEIGHBORS):
    start_preprocess = time.time()
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

    pricing_time = 0
    pgm_time = 0
    lp_solve_time = 0
    model_update_time = 0
    extra_pricing_time = 0
    rci_count = 0
    start_time = time.time()
    model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)    


    column_gen_count = 0
    total_graph_manage_calls = 0
    successful_graph_manage_calls = 0
    graph_manage_count = 0
    continue_iter = True
    while continue_iter:
        continue_inner_optimization = True
        while continue_inner_optimization:
            # OPTIMIZE NEW MODEL
            start_op = time.time()
            model.optimize()
            lp_solve_time += time.time() - start_op
            new_RCIs = identify_violated_ineqs(model, x_ij, RCI_data, customers, end_depot)
            if len(new_RCIs) != 0:
                rci_count += len(new_RCIs)
                start_op = time.time()
                add_RCI_constrs(model, new_RCIs, RCI_constrs)
                model_update_time += time.time() - start_op
                start_op = time.time()
                model.optimize()
                lp_solve_time += time.time() - start_op
            lp_val = model.getObjVal()
            print(f"Model has an LP objective val = {lp_val}")

            # UPDATE N2 AND CONTINUE IF NEGATIVE RC PATH EXISTS
            graph_manage_count += 1
            continue_inner_optimization = False
            start_op = time.time()
            for (l, _) in enumerate(omega_r):
                total_graph_manage_calls += 1
                l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], omega_y_l[l], cover_constrs, RCI_constrs, model)
                if rc < -epsilon:
                    successful_graph_manage_calls += 1
                    continue_inner_optimization = True
                    if len(l_hat_l) > 1:
                        for idx, c1 in enumerate(l_hat_l[:-1]):
                            c2 = l_hat_l[idx + 1]
                            N2_pairs[l].add((c1, c2))

                if (time.time() - start_time) > time_limit:
                    continue_inner_optimization = False
                    continue_iter = False
                    print("Terminating Inner Optimization")
                    break

            # UPDATE ARCS AND EDGES BASED ON NEW N2
            if continue_inner_optimization:
                # GET VIOLATED RCI INEQUALITIES
                # new_RCIs = identify_violated_ineqs(model, x_p, N2_omega_y_l, customers, end_depot, capacity, RCI_subsets)

                # UPDATE GRAPH AND ARC SETS
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
                pgm_time += time.time() - start_op

                # MAKE CHANGES TO MODEL
                start_op = time.time()
                update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
                model_update_time += time.time() - start_op
            else:
                pgm_time += time.time() - start_op

        time_before_CG = time.time()
        if (time.time() - start_time) > time_limit:
            print("Breaking out of loop before CG")
            break
        # COLUMN GEN WHEN INNER OPTIMIZATION FINISHED
        start_op = time.time()
        new_route, new_rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity, RCI_constrs)
        # check_route_reduced_cost_with_RCI(model, RCI_constrs, cover_constrs, customers, start_depot, end_depot, new_route)
        # check_rc_from_matrix(model, new_route, x_ij, capacity)

        if (time.time() - start_time) > time_limit:
            print(f"Breaking out of loop after CG. Time before CG was {round(time_before_CG - start_time, 1)}. Time at break is {round(time.time() - start_time, 1)}")
            extra_pricing_time = time.time() - time_before_CG
            break
        pricing_time += time.time() - start_op

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
            
            start_op = time.time()
            N2_pairs.append(set())
            N2_pairs[-1].update(initial_N2_pairs)

            N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
            N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
            pgm_time += time.time() - start_op

            start_op = time.time()
            add_family_to_model(model, N2_omega_R_plus, N2_omega_y_l, cover_constrs, flow_constrs, x_ij, x_p, RCI_constrs)
            model_update_time += time.time() - start_op

            
    end_LP_time = time.time()
    model.optimize()
    print(f"Finished solving LP in {round(end_LP_time - start_time, 1)} seconds.\nRan column gen {column_gen_count} times.\nCalled graph management {graph_manage_count} times for the last graph.")
    convert_to_ILP(model)
    model.controls.outputlog = 1
    start_op = time.time()
    model.optimize()
    end_time = time.time()
    ILP_solve_time = end_time - start_op
    ILP_val = model.getObjVal()

    print(f"Finished solving ILP in {round(end_time - start_time, 1)} seconds.")

    results = {
        "Algorithm": "Time-Limited Easy-Edge PGM with RCI",
        "Data_set": DATA_SET,
        "Num_customers": len(customers),
        "Capacity_divisor": MY_DIVISOR,
        "Time_limit": time_limit,
        "LP_solve_time": round(lp_solve_time, 2),
        "ILP_solve_time": round(ILP_solve_time, 2),
        "PGM_time": round(pgm_time, 2),
        "Pricing_time": round(pricing_time, 2),
        "Preprocessing_time": round(start_time - start_preprocess, 2),
        "LP_obj_val": round(lp_val, 2),
        "ILP_obj_val": round(ILP_val, 2),
        "Total_time": round((end_time - start_time) - extra_pricing_time, 2),
        "CG_iterations": column_gen_count,
        "PGM_iterations": graph_manage_count,
        "Total_PGM_calls": total_graph_manage_calls,
        "Succseeful_PGM_calls": successful_graph_manage_calls,
        "RCI_constrs_added": rci_count
    }


    write_test_data_to_file(results, "time_limit_PGM_RCI.csv")

            

def PGM_last_graph_no_RCI(DATA_SET, NUM_LA_NEIGHBORS):
    start_preprocess = time.time()
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

    for route in omega_r:
        beta = compute_beta(route, customers)
        omega_y_l.append(compute_omega_y_l(beta, omega_y))
        (edges, nodes) = create_LA_arc_graph(omega_y_l[-1], beta, capacity)
        # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
        omega_R_plus.append((edges, nodes))


    N2_omega_y_l = consistent_N2_arcs(omega_y_l, N2_pairs, [])
    N2_omega_R_plus = consistent_N2_graphs(omega_R_plus, N2_pairs, [])

    pricing_time = 0
    pgm_time = 0
    lp_solve_time = 0
    model_update_time = 0
    extra_pricing_time = 0
    start_time = time.time()
    model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)    


    column_gen_count = 0
    graph_manage_count = 0
    continue_iter = True
    while continue_iter:
        continue_inner_optimization = True
        while continue_inner_optimization:
            # OPTIMIZE NEW MODEL
            start_op = time.time()
            model.optimize()
            lp_solve_time += time.time() - start_op
            lp_val = model.getObjVal()
            print(f"Model has an LP objective val = {lp_val}")

            # UPDATE N2 AND CONTINUE IF NEGATIVE RC PATH EXISTS
            continue_inner_optimization = False
            # for (l, _) in enumerate(omega_r):
            l = len(omega_r) - 1

            start_op = time.time()
            l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], omega_y_l[l], cover_constrs, {}, model)
            graph_manage_count += 1
            if rc < -epsilon:
                continue_inner_optimization = True
                if len(l_hat_l) > 1:
                    for idx, c1 in enumerate(l_hat_l[:-1]):
                        c2 = l_hat_l[idx + 1]
                        N2_pairs[l].add((c1, c2))

            if (time.time() - start_time) > time_limit:
                continue_inner_optimization = False
                continue_iter = False
                print("Terminating Inner Optimization")

            # UPDATE ARCS AND EDGES BASED ON NEW N2
            if continue_inner_optimization:
                # GET VIOLATED RCI INEQUALITIES
                # new_RCIs = identify_violated_ineqs(model, x_p, N2_omega_y_l, customers, end_depot, capacity, RCI_subsets)

                # UPDATE GRAPH AND ARC SETS
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
                pgm_time += time.time() - start_op

                # MAKE CHANGES TO MODEL
                start_op = time.time()
                update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, {})
                model_update_time += time.time() - start_op
            else:
                pgm_time += time.time() - start_op

        time_before_CG = time.time()
        if (time.time() - start_time) > time_limit:
            print("Breaking out of loop before CG")
            break
        # COLUMN GEN WHEN INNER OPTIMIZATION FINISHED
        start_op = time.time()
        new_route, new_rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity)
        # check_route_reduced_cost_with_RCI(model, RCI_constrs, cover_constrs, customers, start_depot, end_depot, new_route)
        # check_rc_from_matrix(model, new_route, x_ij, capacity)

        if (time.time() - start_time) > time_limit:
            print(f"Breaking out of loop after CG. Time before CG was {round(time_before_CG - start_time, 1)}. Time at break is {round(time.time() - start_time, 1)}")
            extra_pricing_time = time.time() - time_before_CG
            break
        pricing_time += time.time() - start_op

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
            
            start_op = time.time()
            N2_pairs.append(set())
            N2_pairs[-1].update(initial_N2_pairs)

            N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
            N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
            pgm_time += time.time() - start_op

            start_op = time.time()
            add_family_to_model(model, N2_omega_R_plus, N2_omega_y_l, cover_constrs, flow_constrs, x_ij, x_p, {})
            model_update_time += time.time() - start_op

            
    end_LP_time = time.time()
    model.optimize()
    print(f"Finished solving LP in {round(end_LP_time - start_time, 1)} seconds.\nRan column gen {column_gen_count} times.\nCalled graph management {graph_manage_count} times for the last graph.")
    convert_to_ILP(model)
    model.controls.outputlog = 1
    start_op = time.time()
    model.optimize()
    end_time = time.time()
    ILP_solve_time = end_time - start_op
    ILP_val = model.getObjVal()

    print(f"Finished solving ILP in {round(end_time - start_time, 1)} seconds.")

    results = {
        "Algorithm": "Time-Limited Last-Graph PGM no RCI",
        "Data_set": DATA_SET,
        "Num_customers": len(customers),
        "Capacity_divisor": MY_DIVISOR,
        "Time_limit": time_limit,
        "LP_solve_time": round(lp_solve_time, 2),
        "ILP_solve_time": round(ILP_solve_time, 2),
        "PGM_time": round(pgm_time, 2),
        "Pricing_time": round(pricing_time, 2),
        "Preprocessing_time": round(start_time - start_preprocess, 2),
        "LP_obj_val": round(lp_val, 2),
        "ILP_obj_val": round(ILP_val, 2),
        "Total_time": round((end_time - start_time) - extra_pricing_time, 2),
        "CG_iterations": column_gen_count,
        "PGM_iterations": graph_manage_count
    }


    write_test_data_to_file(results, "time_limit_PGM_LG_no_RCI.csv")

            
def PGM_easy_edge_no_RCI(DATA_SET, NUM_LA_NEIGHBORS):
    start_preprocess = time.time()
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

    for route in omega_r:
        beta = compute_beta(route, customers)
        omega_y_l.append(compute_omega_y_l(beta, omega_y))
        (edges, nodes) = create_LA_arc_graph(omega_y_l[-1], beta, capacity)
        # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
        omega_R_plus.append((edges, nodes))


    N2_omega_y_l = consistent_N2_arcs(omega_y_l, N2_pairs, [])
    N2_omega_R_plus = consistent_N2_graphs(omega_R_plus, N2_pairs, [])

    pricing_time = 0
    pgm_time = 0
    lp_solve_time = 0
    model_update_time = 0
    extra_pricing_time = 0
    start_time = time.time()
    model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)    


    column_gen_count = 0
    total_graph_manage_calls = 0
    successful_graph_manage_calls = 0
    graph_manage_count = 0
    continue_iter = True
    while continue_iter:
        continue_inner_optimization = True
        while continue_inner_optimization:
            # OPTIMIZE NEW MODEL
            start_op = time.time()
            model.optimize()
            lp_solve_time += time.time() - start_op
            lp_val = model.getObjVal()
            print(f"Model has an LP objective val = {lp_val}")

            # UPDATE N2 AND CONTINUE IF NEGATIVE RC PATH EXISTS
            graph_manage_count += 1
            continue_inner_optimization = False
            start_op = time.time()
            for (l, _) in enumerate(omega_r):
                total_graph_manage_calls += 1
                l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], omega_y_l[l], cover_constrs, {}, model)
                if rc < -epsilon:
                    successful_graph_manage_calls += 1
                    continue_inner_optimization = True
                    if len(l_hat_l) > 1:
                        for idx, c1 in enumerate(l_hat_l[:-1]):
                            c2 = l_hat_l[idx + 1]
                            N2_pairs[l].add((c1, c2))

                if (time.time() - start_time) > time_limit:
                    continue_inner_optimization = False
                    continue_iter = False
                    print("Terminating Inner Optimization")
                    break

            # UPDATE ARCS AND EDGES BASED ON NEW N2
            if continue_inner_optimization:
                # GET VIOLATED RCI INEQUALITIES
                # new_RCIs = identify_violated_ineqs(model, x_p, N2_omega_y_l, customers, end_depot, capacity, RCI_subsets)

                # UPDATE GRAPH AND ARC SETS
                N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
                N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
                pgm_time += time.time() - start_op

                # MAKE CHANGES TO MODEL
                start_op = time.time()
                update_model(model, new_arcs, new_edges, cover_constrs, flow_constrs, x_ij, x_p, {})
                model_update_time += time.time() - start_op
            else:
                pgm_time += time.time() - start_op

        time_before_CG = time.time()
        if (time.time() - start_time) > time_limit:
            print("Breaking out of loop before CG")
            break
        # COLUMN GEN WHEN INNER OPTIMIZATION FINISHED
        start_op = time.time()
        new_route, new_rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity)
        # check_route_reduced_cost_with_RCI(model, RCI_constrs, cover_constrs, customers, start_depot, end_depot, new_route)
        # check_rc_from_matrix(model, new_route, x_ij, capacity)

        if (time.time() - start_time) > time_limit:
            print(f"Breaking out of loop after CG. Time before CG was {round(time_before_CG - start_time, 1)}. Time at break is {round(time.time() - start_time, 1)}")
            extra_pricing_time = time.time() - time_before_CG
            break
        pricing_time += time.time() - start_op

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
            
            start_op = time.time()
            N2_pairs.append(set())
            N2_pairs[-1].update(initial_N2_pairs)

            N2_omega_y_l, new_arcs = consistent_N2_arcs(omega_y_l, N2_pairs, N2_omega_y_l)
            N2_omega_R_plus, new_edges = consistent_N2_graphs(omega_R_plus, N2_pairs, N2_omega_R_plus)
            pgm_time += time.time() - start_op

            start_op = time.time()
            add_family_to_model(model, N2_omega_R_plus, N2_omega_y_l, cover_constrs, flow_constrs, x_ij, x_p, {})
            model_update_time += time.time() - start_op

            
    end_LP_time = time.time()
    model.optimize()
    print(f"Finished solving LP in {round(end_LP_time - start_time, 1)} seconds.\nRan column gen {column_gen_count} times.\nCalled graph management {graph_manage_count} times for the last graph.")
    convert_to_ILP(model)
    model.controls.outputlog = 1
    start_op = time.time()
    model.optimize()
    end_time = time.time()
    ILP_solve_time = end_time - start_op
    ILP_val = model.getObjVal()

    print(f"Finished solving ILP in {round(end_time - start_time, 1)} seconds.")

    results = {
        "Algorithm": "Time-Limited Easy-Edge PGM no RCI",
        "Data_set": DATA_SET,
        "Num_customers": len(customers),
        "Capacity_divisor": MY_DIVISOR,
        "Time_limit": time_limit,
        "LP_solve_time": round(lp_solve_time, 2),
        "ILP_solve_time": round(ILP_solve_time, 2),
        "PGM_time": round(pgm_time, 2),
        "Pricing_time": round(pricing_time, 2),
        "Preprocessing_time": round(start_time - start_preprocess, 2),
        "LP_obj_val": round(lp_val, 2),
        "ILP_obj_val": round(ILP_val, 2),
        "Total_time": round((end_time - start_time) - extra_pricing_time, 2),
        "CG_iterations": column_gen_count,
        "PGM_iterations": graph_manage_count,
        "Total_PGM_calls": total_graph_manage_calls,
        "Succseeful_PGM_calls": successful_graph_manage_calls
    }


    write_test_data_to_file(results, "time_limit_PGM_no_RCI.csv")

            


def time_limited_CG(DATA_SET):
    preprocess_start = time.time()
    MYDIVISOR = 1
    NUM_LA_NEIGHBORS = 0
    CUSTOMER_SIZE_LIMIT = 200
    customers, start_depot, end_depot, capacity = generate_problem(
        DATA_SET, MYDIVISOR, NUM_LA_NEIGHBORS, CUSTOMER_SIZE_LIMIT)

    cust_by_id = {}
    for u in customers + [start_depot, end_depot]:
        cust_by_id[u.id] = u

    omega_r = initialize_omega_r(start_depot, customers, end_depot)

    print("Building model")
    start_time = time.time()
    RMP_model, cover_constrs = create_RMP_model(omega_r, customers)
    model_update_time = time.time() - start_time

    print("Done building model")

    # GENERATE NEW COLUMN, UPDATE MODEL, SOLVE AND REPEAT
    continue_iter = True
    cg_count = 0
    pricing_time = 0
    lp_solve_time = 0
    # print("Entering loop")
    while continue_iter:
        if (time.time() - start_time) > time_limit:
            break
        # print("Optimizing")
        start_op = time.time()
        RMP_model.solve()
        lp_solve_time += time.time() - start_op
        lp_val = RMP_model.getObjVal()
        # print("Done optimizing")

        # print("Calling pricing")
        start_op = time.time()
        time_left = time_limit - (start_op - start_time)
        new_cols, excess_cg_time = partial_pricing(RMP_model, cover_constrs, customers, start_depot, end_depot, capacity, time_limit=time_left)
        pricing_time += time.time() - start_op

        if len(new_cols) == 0:
            print(f"Done interating. No new routes")
            continue_iter = False
        else:
            start_op = time.time()
            for new_col in new_cols:
                cg_count += 1
                # print(f"Adding Column {new_col.id}")
                add_col_to_model(RMP_model, cover_constrs, new_col, customers)
                omega_r.append(new_col)
            model_update_time += time.time() - start_op

    

    convert_to_ILP(RMP_model)
    RMP_model.controls.outputlog = 1
    start_op = time.time()
    RMP_model.solve()
    end_time = time.time()
    ILP_val = RMP_model.getObjVal()
    ILP_solve_time = end_time - start_op

    print(f"\nColumn Gen finished with {cg_count} iterations in {round(end_time - start_time, 1)} seconds.\n")


    results = {
        "Algorithm": "Time-limited CG with partial pricing",
        "Data_set": DATA_SET,
        "Num_customers": len(customers),
        "Capacity_divisor": MYDIVISOR,
        "Time_limit": time_limit,
        "LP_solve_time": round(lp_solve_time, 2),
        "ILP_solve_time": round(ILP_solve_time, 2),
        "Pricing_time": round(pricing_time, 2),
        "Model_update_time": round(model_update_time, 2),
        "Preprocessing_time": round(start_time - preprocess_start, 2),
        "LP_obj_val": round(lp_val, 2),
        "ILP_obj_val": round(ILP_val, 2),
        "Total_time": round((end_time - start_time) - excess_cg_time, 2),
        "CG_iterations": cg_count,
    }


    write_test_data_to_file(results, "time_limit_CG_partial_pricing.csv")



# def run_with_timeout(max_time, function, *args):
#     # Create a multiprocessing queue to store the result
#     queue = multiprocessing.Queue()
    
#     # Wrapper function to run the function and put the result in the queue
#     def wrapper(queue, function, *args):
#         result = function(*args)
#         queue.put(result)
    
#     # Create a separate process
#     process = multiprocessing.Process(target=wrapper, args=(queue, function, *args))
#     process.start()

#     # Wait for the process to complete or timeout
#     process.join(max_time)
    
#     if process.is_alive():
#         process.terminate()  # Kill the process if it's still running
#         process.join()       # Ensure the process is properly cleaned up
#         return f"Function took too long and was terminated after {max_time}."
#     else:
#         # Return the result from the queue
#         return queue.get()
