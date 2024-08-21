import numpy as np
import math
from debug.col_gen import check_route_not_in_graph
from debug.RMP import count_constrs, show_routes_traversed
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col, column_gen
from utilities.update_model import add_col_to_model
from utilities.compute_beta import compute_beta, create_graph_from_beta, create_meta_graph, create_family_from_meta_graph, create_LA_arc_graph
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l
from models.lp_models.RMP import create_RMP_model, create_RMP_ILP_model
from models.lp_models.RMP_omega_R_plus import create_RMP_GM_model, create_RMP_GM_ILP_model
from models.lp_models.RMP_GM_plus_LA import create_RMP_GM_LA_model
from models.data_structures.customer import Customer


epsilon = 0.00001


def solve_MP_with_CG():
    data_set = "A-n32-k5.vrp"
    mydivisor = 20
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, mydivisor)

    cust_by_id = {}
    for u in customers + [start_depot, end_depot]:
        cust_by_id[u.id] = u

    omega_r = initialize_omega_r(start_depot, customers, end_depot)

    RMP_model = create_RMP_model(omega_r, customers)

    # GENERATE NEW COLUMN, UPDATE MODEL, SOLVE AND REPEAT
    continue_iter = True
    cg_count = 0
    while continue_iter:
        RMP_model.optimize()

        new_col, rc = generate_col(
            RMP_model, customers, start_depot, end_depot, capacity)

        cg_count += 1
        if rc >= -epsilon:
            print(f"Done interating. RC = {rc}")
            continue_iter = False
        else:
            print(f"Adding Column {new_col.id}")
            RMP_model = add_col_to_model(RMP_model, new_col, customers)
            omega_r.append(new_col)

    RMP_model.setParam('OutputFlag', 1)
    RMP_model.optimize()

    ILP_model = create_RMP_ILP_model(omega_r, customers)
    ILP_model.optimize()

    routes_traversed = [
        var.varName for var in ILP_model.getVars() if var.x > 0.99 and var.x < 1.01]

    print("Routes taken:")
    for route in routes_traversed:
        print(route)

    print(f"Column Generation finished with {cg_count} columns added")

    # Accept user inputs for debugging purposes
    continue_iter = True
    while continue_iter:
        no_new_cust = False
        check_route = [start_depot]
        while not no_new_cust:
            new_cust = input("Enter customer to add to route (or 'end'):")
            if new_cust != "end":
                new_customer = cust_by_id[str(new_cust)]
                check_route.append(new_customer)
            else:
                check_route.append(end_depot)
                no_new_cust = True

        distances = []
        duals = []
        demands = []

        for (idx, u) in enumerate(check_route[1:-1]):
            v = check_route[idx]
            distances.append(math.hypot(u.x - v.x, u.y - v.y))
            duals.append(RMP_model.getConstrByName(f"cover_{u.id}").Pi)
            demands.append(u.demand)

        distances.append(math.hypot(u.x - end_depot.x, u.y - end_depot.y))
        total_dist = sum(distances)
        total_dual = sum(duals)

        print(f"All distances traveled: {distances}")
        print(f"Duals of customers visited: {duals}")
        print(
            f"Reduced cost of route = {total_dist} - {total_dual} = {total_dist - total_dual}")
        print(
            f"Feasibility check: all demands: {demands} total demand: {sum(demands)} capacity: {capacity}")


def solve_MP_CG_GM():
    data_set = "A-n32-k5.vrp"
    mydivisor = 20
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, mydivisor)

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]

    beta = compute_beta(omega_r[0], customers)
    (edges, nodes) = create_graph_from_beta(beta, capacity)
    omega_r_plus = [(edges, nodes)]

    # SOLVE THE RMP, GENERATE NEW COLUMN, SOLVE AGAIN
    model = create_RMP_GM_model(
        omega_r_plus, customers, start_depot, end_depot)

    continue_iter = True
    iter_count = 0
    while continue_iter:
        model.optimize()
        # count_constrs(model, customers, omega_r_plus)

        new_route, rc = generate_col(
            model, customers, start_depot, end_depot, capacity)

        if rc >= -epsilon:
            print(f"Done solving. Non-negative reduced cost: rc = {rc}")
            beta = compute_beta(new_route, customers)
            (edges, nodes) = create_graph_from_beta(beta, capacity)
            # check_route_not_in_graph(new_route, edges)
            continue_iter = False
        else:
            iter_count += 1
            omega_r.append(new_route)
            beta = compute_beta(new_route, customers)
            (edges, nodes) = create_graph_from_beta(beta, capacity)
            # check_route_not_in_graph(new_route, edges)

            omega_r_plus.append((edges, nodes))
            model = create_RMP_GM_model(
                omega_r_plus, customers, start_depot, end_depot)

    model.setParam('OutputFlag', 1)
    model.optimize()

    ILP_model = create_RMP_GM_ILP_model(
        omega_r_plus, customers, start_depot, end_depot)
    ILP_model.optimize()

    show_routes_traversed(ILP_model)


def solve_MP_CG_GM2():
    data_set = "A-n32-k5.vrp"
    mydivisor = 20
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, mydivisor)

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]

    beta = compute_beta(omega_r[0], customers)
    meta_edges, nodes = create_meta_graph(
        customers, start_depot, end_depot, capacity)
    edges = create_family_from_meta_graph(meta_edges, beta)
    omega_r_plus = [(edges, nodes)]

    # SOLVE THE RMP, GENERATE NEW COLUMN, SOLVE AGAIN
    model = create_RMP_GM_model(
        omega_r_plus, customers, start_depot, end_depot)

    continue_iter = True
    while continue_iter:
        model.optimize()
        # count_constrs(model, customers, omega_r_plus)

        new_route, rc = generate_col(
            model, customers, start_depot, end_depot, capacity)

        if rc >= -epsilon:
            print(f"Done solving. Non-negative reduced cost: rc = {rc}")
            # beta = compute_beta(new_route, customers)
            # edges = create_family_from_meta_graph(meta_edges, beta)
            # check_route_not_in_graph(new_route, edges)
            continue_iter = False
        else:
            omega_r.append(new_route)
            beta = compute_beta(new_route, customers)
            edges = create_family_from_meta_graph(meta_edges, beta)
            # check_route_not_in_graph(new_route, edges)

            omega_r_plus.append((edges, nodes))
            model = create_RMP_GM_model(
                omega_r_plus, customers, start_depot, end_depot)

    model.setParam('OutputFlag', 1)
    model.optimize()

    ILP_model = create_RMP_GM_ILP_model(
        omega_r_plus, customers, start_depot, end_depot)
    ILP_model.optimize()

    show_routes_traversed(ILP_model)


def solve_MP_GM_LA():
    data_set = "A-n32-k5.vrp"
    mydivisor = 20
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, mydivisor)

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]

    beta = compute_beta(omega_r[0], customers)
    omega_y = find_LA_arcs(customers, end_depot, capacity)
    omega_y_l = [compute_omega_y_l(beta, omega_y)]
    (edges, nodes) = create_LA_arc_graph(omega_y_l[0], beta, capacity)
    print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
    omega_R_plus = [(edges, nodes)]

    model = create_RMP_GM_LA_model(
        omega_R_plus, omega_y_l, customers, start_depot, end_depot)

    continue_iter = True
    while continue_iter:
        model.optimize()

        new_route, rc = generate_col(
            model, customers, start_depot, end_depot, capacity)

        if rc >= -epsilon:
            print(f"Done solving. Non-negative reduced cost: rc = {rc}")

            continue_iter = False
        else:
            print(f"Negative reduced cost: rc = {rc}")
            omega_r.append(new_route)
            beta = compute_beta(new_route, customers)
            omega_y_l.append(compute_omega_y_l(beta, omega_y))
            (edges, nodes) = create_LA_arc_graph(omega_y_l[-1], beta, capacity)

            omega_R_plus.append((edges, nodes))
            model = create_RMP_GM_LA_model(
                omega_R_plus, omega_y_l, customers, start_depot, end_depot)


# solve_MP_with_CG()
# solve_MP_CG_GM()
# solve_MP_CG_GM2()
solve_MP_GM_LA()


#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#

# DEBUGGING CODE

# print(
#     f"Route: {[u.id for u in omega_r[0].visits]} Beta: {[u.id for u in beta]}")
# print(f"Edges in graph: {len(edges)}")
# RMP_model = create_RMP_model(omega_r, customers)

# # GENERATE NEW COLUMN, UPDATE MODEL, SOLVE AND REPEAT
# continue_iter = True
# while continue_iter:
#     RMP_model.optimize()

#     new_col, rc = generate_col(
#         RMP_model, customers, start_depot, end_depot, capacity)

#     if rc >= -epsilon:
#         print(f"Done interating. RC = {rc}")
#         continue_iter = False
#     else:
#         print(f"Adding Column {new_col.id}")
#         RMP_model = add_col_to_model(RMP_model, new_col, customers)
#         omega_r.append(new_col)

# RMP_model.setParam('OutputFlag', 1)
# RMP_model.optimize()
