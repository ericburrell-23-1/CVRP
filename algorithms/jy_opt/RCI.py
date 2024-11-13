import xpress as xp
import numpy as np
from models.data_structures.customer import Customer
from utilities.RCI.identify_violated_inequalities import compute_violations, MAX_VIOLATIONS_COUNT

def identify_violated_ineqs(model: xp.problem, vars: dict, RCI_data: tuple, N: list):
    (B_matrix, rhs_vector, row_index, col_index, all_N_hat) = RCI_data

    # INITIALIZE X_UV VALUES TO 0
    x_uv_vals = {}
    # x_uv_vars = {}
    for u in N:
        for v in N + [-2]:
            if u == v:
                continue
            x_uv_vals[u, v] = 0
            # x_uv_vars[col_index[u, v]] = []

    # SUM SOLUTION IN X_UV
    for var_name in vars:
        (edge_name, beta_idx) = var_name
        u = edge_name[0]
        v = edge_name[2]

        if u == -1 or u == v:
            continue
        sol = model.getSolution(vars[var_name])
        # x_uv_vars[col_index[u, v]].append(vars[var_name])
        # if sol > 0:
        x_uv_vals[u, v] += sol

    # BUILD X VECTOR AS NUMPY ARRAY
    x_vector = np.zeros(len(col_index))
    for (u_id, v_id), value in x_uv_vals.items():
        if (u_id, v_id) in col_index:
            col_idx = col_index[(u_id, v_id)]
            x_vector[col_idx] = value

    lhs_vector = B_matrix.dot(x_vector)

    violations = compute_violations(lhs_vector, rhs_vector, row_index)

    # violated_ineqs = []
    jy_RCI = {}
    for v in violations[:MAX_VIOLATIONS_COUNT]:
        (N_hat_name, violation_amount, row_idx) = v
        if violation_amount < -0.0001:
            N_hat = tuple([u.id for u in all_N_hat[N_hat_name].N_hat])
            jy_RCI[N_hat] = rhs_vector[N_hat_name]
            # row = B_matrix.getrow(row_idx)
            # nonzero_col_indices = row.nonzero()[1]
            # lhs_terms = []
            # for col_idx in nonzero_col_indices:
            #     lhs_terms.extend(x_uv_vars[col_idx])

            # rhs_val = rhs_vector[N_hat_name]
            # N_hat = all_N_hat[N_hat_name]
            # violated_ineqs.append((lhs_terms, rhs_val, N_hat))
        else:
            break

    return jy_RCI #violated_ineqs
