import numpy as np
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.update_model import add_col_to_model
from models.lp_models.RMP import create_RMP_model


epsilon = 0.00001


def solve_MP_with_CG():
    data_set = "A-n32-k5.vrp"
    mydivisor = 20
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, mydivisor)

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

    print(f"Column Generation finished with {cg_count} columns added")


solve_MP_with_CG()
