import time
import xpress as xp
from debug.RMP_GM_LA import show_graph_edges_in_solution, show_LA_arcs_in_solution, compute_cost_from_LA_arcs_selected, compute_cost_from_routes_departing_depot, check_coverage_over_arcs, check_reduced_cost_of_gen_col
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.compute_beta import compute_beta, create_LA_arc_graph
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l
from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model
from models.data_structures.customer import Customer


epsilon = 0.00001


def solve_MP_GM_LA(data_set, NUM_LA_NEIGHBORS):
    MYDIVISOR = 20
    CUSTOMER_SIZE_LIMIT = 200
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, MYDIVISOR, NUM_LA_NEIGHBORS, CUSTOMER_SIZE_LIMIT)

    customers_by_id = {}
    for u in customers + [start_depot, end_depot]:
        customers_by_id[u.id] = u

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]
    omega_y = find_LA_arcs(customers, end_depot, capacity)
    omega_y_l = []
    omega_R_plus = []

    iter_start_time = time.time()
    for route in omega_r:
        beta = compute_beta(route, customers)
        omega_y_l.append(compute_omega_y_l(beta, omega_y))
        (edges, nodes) = create_LA_arc_graph(omega_y_l[-1], beta, capacity)
        # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
        omega_R_plus.append((edges, nodes))

    model, cover_constrs, x_ij, x_p = create_RMP_GM_LA_model(
        omega_R_plus, omega_y_l, customers, start_depot, end_depot)

    continue_iter = True
    iter_count = 0
    cg_count = 1
    while continue_iter:
        model.optimize()
        iter_count += 1
        print(f"Model has an LP objective val = {model.getObjVal()}")
        # show_graph_edges_in_solution(x_ij, model)
        # show_LA_arcs_in_solution(x_p, model)
        # compute_cost_from_LA_arcs_selected(x_p, model, omega_y_l)
        # compute_cost_from_routes_departing_depot(
        #     x_ij, model, customers, start_depot)
        # check_coverage_over_arcs(x_p, model, customers)

        new_route, rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity)
        # check_reduced_cost_of_gen_col(new_route, model, cover_constrs)

        # check_route = Route([start_depot, customers[0], customers[0]],
        #                     customers, start_depot, end_depot)
        # check_route = Route([start_depot, customers[0], customers[2],
        #                     customers[1], end_depot], customers, start_depot, end_depot)
        # check_reduced_cost_of_gen_col(check_route, model, cover_constrs)

        if rc >= -epsilon:
            iter_end_time = time.time()
            print(
                f"Done solving. Non-negative reduced cost: rc = {round(rc, 4)}\n")

            continue_iter = False
        else:
            cg_count += 1
            step_time_start = time.time()
            omega_r.append(new_route)
            step_time_end = time.time()
            print(f"Spent {round(step_time_end - step_time_start, 2)} seconds adding new route to omega_r")
            step_time_start = time.time()
            beta = compute_beta(new_route, customers)
            step_time_end = time.time()
            print(f"Spent {round(step_time_end - step_time_start, 2)} seconds computing beta")
            step_time_start = time.time()
            omega_y_l.append(compute_omega_y_l(beta, omega_y))
            step_time_end = time.time()
            print(f"Spent {round(step_time_end - step_time_start, 2)} seconds computing omega_y_l")
            # route_arcs = omega_y_l[-1].get((new_route.visits[1].id,
            #                                 new_route.visits[-1].id, new_route.demand), [None])
            # for arc in route_arcs:
            #     print(f"route_arc: {[c.id for c in arc.visits]}")
            step_time_start = time.time()
            omega_R_plus.append(create_LA_arc_graph(
                omega_y_l[-1], beta, capacity))
            step_time_end = time.time()
            print(f"Spent {round(step_time_end - step_time_start, 2)} seconds creating LA-Arc graph")
            # check_route_reduced_cost(
            #     model, cover_constrs, customers, start_depot, end_depot, new_route)
            # print("Omega_r so far:")
            # for route in omega_r:
            #     print([c.id for c in route.visits])
            step_time_start = time.time()
            model, cover_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                omega_R_plus, omega_y_l, customers, start_depot, end_depot)
            step_time_end = time.time()
            print(f"Spent {round(step_time_end - step_time_start, 2)} seconds building new model")
            print(f"Negative reduced cost: rc = {round(rc, 4)}\n")

            # user_iter = True
            # while user_iter:
            #     u = input("Let's get the LA arcs for you. What is u's id?:")
            #     v = input(
            #         f"{u}'s LA-neighbors are {[lan.id for lan in customers_by_id[u].LA_neighbors]} v's id?:")
            #     d = input("d?:")

            #     y = (u, v, int(d))
            #     arcs = []
            #     for arc in omega_y.get(y, [None]):
            #         if arc == None:
            #             arcs = 'none'
            #         else:
            #             arcs.append([c.id for c in arc.visits])

            #     print(f"All Arcs for {y}: {arcs}")

            #     cont = input("'stop' to end, else go again:")
            #     if cont == "stop":
            #         user_iter = False

    model.controls.outputlog = 1
    model.optimize()
    print(f"Easy PGM finished with {iter_count} solving iterations, {cg_count} columns generated, in {round(iter_end_time - iter_start_time, 1)} iteration time.")
