import numpy as np
import math
import time
import xpress as xp
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.model_updates.update_CG import add_col_to_model
from models.data_structures.route import Route
from models.lp_models.RMP import create_RMP_model, create_RMP_ILP_model
from models.lp_models.RMP_GM_LA import convert_to_ILP
from models.data_structures.customer import Customer

epsilon = 0.00001

def solve_MP_with_CG(data_set):
    preprocess_start = time.time()
    MYDIVISOR = 2
    NUM_LA_NEIGHBORS = 0
    CUSTOMER_SIZE_LIMIT = 200
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, MYDIVISOR, NUM_LA_NEIGHBORS, CUSTOMER_SIZE_LIMIT)

    cust_by_id = {}
    for u in customers + [start_depot, end_depot]:
        cust_by_id[u.id] = u

    omega_r = initialize_omega_r(start_depot, customers, end_depot)

    start_time = time.time()
    RMP_model, cover_constrs = create_RMP_model(omega_r, customers)
    model_update_time = time.time() - start_time

    # GENERATE NEW COLUMN, UPDATE MODEL, SOLVE AND REPEAT
    continue_iter = True
    pricing_time = 0
    lp_solve_time = 0
    cg_count = 0
    while continue_iter:
        start_op = time.time()
        RMP_model.solve()
        lp_solve_time += time.time() - start_op

        start_op = time.time()
        new_col, rc = generate_col(
            RMP_model, cover_constrs, customers, start_depot, end_depot, capacity)
        pricing_time += time.time() - start_op

        cg_count += 1
        if rc >= -epsilon:
            print(f"Done interating. RC = {rc}")
            continue_iter = False
        else:
            print(f"Adding Column {new_col.id}")
            start_op = time.time()
            add_col_to_model(RMP_model, cover_constrs, new_col, customers)
            model_update_time += time.time() - start_op
            omega_r.append(new_col)

    # convert_to_ILP(RMP_model)
    RMP_model.controls.outputlog = 1
    RMP_model.solve()
    end_LP_time = time.time()

    print(f"\nColumn Gen finished with {cg_count} iterations in {round(end_LP_time - start_time, 1)} seconds.\n")

    # theta = []
    # for l in omega_r:
    #     theta.append(f"theta_{l.id}")

    # for l in theta:
    #     solution = RMP_model.getSolution(l)
    #     if solution > 0:
    #         print(f"{l} = {solution}")

    ILP_model = create_RMP_ILP_model(omega_r, customers)
    ILP_model.solve()

    iter_end_time = time.time()

    print(f"\nILP solved after {round(iter_end_time - start_time, 1)} seconds total.")


    # routes_traversed = [
    #     var.name for var in ILP_model.getVariable() if 0.99 < ILP_model.getSolution(var) < 1.01]

    # print("Routes taken:")
    # for route in routes_traversed:
    #     print(route)

    # print(f"Column Generation finished with {cg_count} columns added")

    # # Accept user inputs for debugging purposes
    # continue_iter = True
    # while continue_iter:
    #     no_new_cust = False
    #     check_route = [start_depot]
    #     while not no_new_cust:
    #         new_cust = input("Enter customer to add to route (or 'end'):")
    #         if new_cust != "end":
    #             new_customer = cust_by_id[str(new_cust)]
    #             check_route.append(new_customer)
    #         else:
    #             check_route.append(end_depot)
    #             no_new_cust = True

    #     distances = []
    #     duals = []
    #     demands = []

    #     for (idx, u) in enumerate(check_route[1:-1]):
    #         v = check_route[idx]
    #         distances.append(math.hypot(u.x - v.x, u.y - v.y))
    #         duals.append(RMP_model.getConstrByName(f"cover_{u.id}").Pi)
    #         demands.append(u.demand)

    #     distances.append(math.hypot(u.x - end_depot.x, u.y - end_depot.y))
    #     total_dist = sum(distances)
    #     total_dual = sum(duals)

    #     print(f"All distances traveled: {distances}")
    #     print(f"Duals of customers visited: {duals}")
    #     print(
    #         f"Reduced cost of route = {total_dist} - {total_dual} = {total_dist - total_dual}")
    #     print(
    #         f"Feasibility check: all demands: {demands} total demand: {sum(demands)} capacity: {capacity}")

