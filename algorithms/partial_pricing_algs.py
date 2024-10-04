import numpy as np
import math
import time
import xpress as xp
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.partial_pricing import partial_pricing
from utilities.model_updates.update_CG import add_col_to_model
from models.data_structures.route import Route
from models.lp_models.RMP import create_RMP_model, create_RMP_ILP_model
from models.lp_models.RMP_GM_LA import convert_to_ILP
from models.data_structures.customer import Customer
from data.print_results import write_test_data_to_file

epsilon = 0.00001

def CG_partial_pricing(data_set):
    preprocess_start = time.time()
    MYDIVISOR = 1
    NUM_LA_NEIGHBORS = 0
    CUSTOMER_SIZE_LIMIT = 200
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, MYDIVISOR, NUM_LA_NEIGHBORS, CUSTOMER_SIZE_LIMIT)

    cust_by_id = {}
    for u in customers + [start_depot, end_depot]:
        cust_by_id[u.id] = u

    omega_r = initialize_omega_r(start_depot, customers, end_depot)

    print("Building model")
    start_time = time.time()
    RMP_model, cover_constrs = create_RMP_model(omega_r, customers)
    print("Done building model")

    # GENERATE NEW COLUMN, UPDATE MODEL, SOLVE AND REPEAT
    continue_iter = True
    cg_count = 0
    pricing_time = 0
    model_update_time = 0
    lp_solve_time = 0
    print("Entering loop")
    while continue_iter:
        print("Optimizing")
        start_op = time.time()
        RMP_model.solve()
        lp_solve_time += time.time() - start_op
        lp_val = RMP_model.getObjVal()
        print("Done optimizing")

        print("Calling pricing")
        start_op = time.time()
        new_cols = partial_pricing(RMP_model, cover_constrs, customers, start_depot, end_depot, capacity)
        pricing_time += time.time() - start_op

        if len(new_cols) == 0:
            print(f"Done interating. No new routes")
            continue_iter = False
        else:
            start_op = time.time()
            for new_col in new_cols:
                cg_count += 1
                print(f"Adding Column {new_col.id}")
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

    # theta = []
    # for l in omega_r:
    #     theta.append(f"theta_{l.id}")

    # for l in theta:
    #     solution = RMP_model.getSolution(l)
    #     if solution > 0:
    #         print(f"{l} = {solution}")

    # ILP_model = create_RMP_ILP_model(omega_r, customers)
    # ILP_model.solve()

    results = {
        "Algorithm": "CG with partial pricing",
        "Data_set": data_set,
        "Num_customers": len(customers),
        "Capacity_divisor": MYDIVISOR,
        "Time_limit": "None",
        "LP_solve_time": round(lp_solve_time, 2),
        "ILP_solve_time": round(ILP_solve_time, 2),
        "Pricing_time": round(pricing_time, 2),
        "Preprocessing_time": round(start_time - preprocess_start, 2),
        "LP_obj_val": round(lp_val, 2),
        "ILP_obj_val": round(ILP_val, 2),
        "Total_time": round((end_time - start_time), 2),
        "CG_iterations": cg_count,
    }


    write_test_data_to_file(results, "CG_partial_pricing.csv")
