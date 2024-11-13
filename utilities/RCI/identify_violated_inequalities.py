import math
import numpy as np
import scipy.sparse as sp
import xpress as xp
from models.data_structures.customer import Customer
from utilities.LA_arcs import powerset
MAX_VIOLATIONS_COUNT = 30
epsilon = 0.00001

class RCI_subset:
    def __init__(self, N_hat):
        self.N_hat = sorted(N_hat, key=lambda c: c.id)
        self.name = self.build_name()
        self.demand = self.compute_tot_demand()

    def __eq__(self, other):
        if isinstance(other, RCI_subset):
            if other.name == self.name:
                return True
        return False
    
    def __hash__(self):
        return hash(self.name)

    def build_name(self):
        name = f"{self.N_hat[0].id}"
        if len(self.N_hat) > 1:
            for c in self.N_hat[1:]:
                name += f"_{c.id}"
        return name
    
    def compute_tot_demand(self):
        tot_demand = 0
        for c in self.N_hat:
            tot_demand += c.demand
        return tot_demand



def all_candidate_subsets(customers: list, start_depot: Customer):
    subsets = set()
    for u in customers:
        cust_set = set(u.closest_neighbors[:6] + [u]) - {start_depot}
        for N_hat in powerset(cust_set):
            if len(N_hat) == 0:
                continue
            else:
                subsets.add(RCI_subset(N_hat))

    return subsets


# def get_a_coeff(N_hat, arc, customers, end_depot):
#     a = 0
#     for u in N_hat:
#         for v in set(customers + [end_depot]) - set(N_hat):
#             if (u.id, v.id) in arc.a_uvp:
#                 a += 1

#     return a


def RCI_preprocessing(customers: list, start_depot: Customer, end_depot: Customer, capacity: int):
    RCI_subsets = all_candidate_subsets(customers, start_depot)

    row_index = {}
    col_index = {}
    rhs_vector = {}
    edge_contrib = {}
    all_N_hat = {}

    # COMPUTE COLUMN INDICIES FOR EDGES
    col_idx = 0
    for u in customers:
        for v in customers + [end_depot]:
            if u.id == v.id:
                continue
            else:
                col_index[u.id, v.id] = col_idx
                col_idx += 1
    
    # COMPUTE ROW INDICES FOR RCI SUBSETS
    row_idx = 0
    for N_hat in RCI_subsets:
        rhs_vector[N_hat.name] = math.ceil((N_hat.demand / capacity) - epsilon)
        all_N_hat[N_hat.name] = N_hat
        row_index[N_hat.name] = row_idx
        row_idx += 1
        # RECORD THE INDICES OF THE COLUMNS THAT ARE NONZERO FOR THIS ROW
        edge_contrib[N_hat.name] = set()
        for u in N_hat.N_hat:
            for v in set(customers + [end_depot]) - set(N_hat.N_hat):
                edge_contrib[N_hat.name].add(col_index[u.id, v.id])


    sparse_matrix = sp.lil_matrix((len(row_index), len(col_index)), dtype=int)

    for N_hat in RCI_subsets:
        row_idx = row_index[N_hat.name]
        for col_idx in edge_contrib[N_hat.name]:
            sparse_matrix[row_idx, col_idx] = 1

    B_matrix = sparse_matrix.tocsr()

    RCI_data = (B_matrix, rhs_vector, row_index, col_index, all_N_hat)

    return RCI_data



def compute_violations(lhs_vector, rhs_vector, row_index):
    violations = []
    for N_hat_name, rhs_val in rhs_vector.items():
        row_idx = row_index[N_hat_name]
        lhs_val = lhs_vector[row_idx]

        if rhs_val == 0:
            continue
        violation_amount = (lhs_val - rhs_val) / rhs_val
        violations.append((N_hat_name, violation_amount, row_idx))

    sorted_violations = sorted(violations, key=lambda v: v[1])

    return sorted_violations


def identify_violated_ineqs(model: xp.problem, x_ij: dict, RCI_data: tuple, customers: list, end_depot: Customer):
    (B_matrix, rhs_vector, row_index, col_index, all_N_hat) = RCI_data

    # INITIALIZE X_UV VALUES TO 0
    x_uv_vals = {}
    x_uv_vars = {}
    for u in customers:
        for v in customers + [end_depot]:
            if u.id == v.id:
                continue
            x_uv_vals[u.id, v.id] = 0
            x_uv_vars[col_index[u.id, v.id]] = []

    # SUM SOLUTION IN X_UV
    for l in x_ij:
        for (i_name, j_name) in x_ij[l]:
            if i_name[:5] == "start":
                continue
            sol = model.getSolution(x_ij[l][i_name, j_name])
            u_id = i_name.split("_")[0]
            v_id = j_name.split("_")[0]
            x_uv_vars[col_index[u_id, v_id]].append(x_ij[l][i_name, j_name])
            if sol > 0:
                x_uv_vals[u_id, v_id] += sol

    # BUILD X VECTOR AS NUMPY ARRAY
    x_vector = np.zeros(len(col_index))
    for (u_id, v_id), value in x_uv_vals.items():
        if (u_id, v_id) in col_index:
            col_idx = col_index[(u_id, v_id)]
            x_vector[col_idx] = value

    lhs_vector = B_matrix.dot(x_vector)

    violations = compute_violations(lhs_vector, rhs_vector, row_index)

    violated_ineqs = []
    for v in violations[:MAX_VIOLATIONS_COUNT]:
        if v[1] < -0.0001:
            row = B_matrix.getrow(v[2])
            nonzero_col_indices = row.nonzero()[1]
            lhs_terms = []
            for col_idx in nonzero_col_indices:
                lhs_terms.extend(x_uv_vars[col_idx])

            rhs_val = rhs_vector[v[0]]
            N_hat = all_N_hat[v[0]]
            violated_ineqs.append((lhs_terms, rhs_val, N_hat))
        else:
            break

    return violated_ineqs

    








# def identify_violated_ineqs(model: xp.problem, x_p: dict, omega_y_l: list, customers: list, end_depot: Customer, capacity: int, all_N_hat: set):
#     violations = []

#     for N_hat in all_N_hat:
#         # COMPUTE RHS OF RCI CONSTRAINT
#         lhs = 0
#         lhs_terms = []
#         for l, omega_y in enumerate(omega_y_l):
#             for y in omega_y:
#                 for arc in omega_y[y]:
#                     a_N_hat_p = get_a_coeff(N_hat, arc, customers, end_depot)
#                     arc_sol = model.getSolution(x_p[l][arc.id])
#                     lhs += (a_N_hat_p * arc_sol)
#                     lhs_terms.append(x_p[l][arc.id] * a_N_hat_p)

#         # COMPUTE LHS
#         rhs = 0
#         for c in N_hat:
#             rhs += c.demand

#         rhs = math.ceil((rhs / capacity) - epsilon)

#         if rhs > 0:
#             violation_amount = (lhs - rhs) / rhs

#             if violation_amount < 0:
#                 violations.append((violation_amount, lhs_terms, rhs, N_hat))
#         else:
#             print(f"rhs == 0 for N_hat = {N_hat}")
        

#     if len(violations) > MAX_VIOLATIONS_COUNT:
#         most_violated = sorted(violations, key=lambda v: v[0])
#         print(f"Found {MAX_VIOLATIONS_COUNT} violated RCI constraints")
#         return most_violated[:MAX_VIOLATIONS_COUNT]
    
#     print(f"Found {len(violations)} violated RCI constraints")
#     return violations
