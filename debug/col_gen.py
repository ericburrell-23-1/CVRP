import math
import numpy as np


def check_route_not_in_graph(route, edges):
    for u in route.visits[:-1]:
        v = route.visits[route.visits.index(u) + 1]
        violation = True
        for (i, j) in edges:
            if i.u == u and j.u == v:
                violation = False
                break
        if violation == True:
            print(
                f"❌ Edge containing {u.id} -> {v.id} not in new graph")


def check_route_reduced_cost(model, constraints, customers, start_depot, end_depot, route):
    dist = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            dist[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    cost_sum = 0
    for (idx, u) in enumerate(route.visits[:-1]):
        v = route.visits[idx + 1]
        cost_sum += dist[u.id, v.id]

    dual_sum = 0
    for u in route.visits[1:-1]:
        dual_sum += model.getDual(constraints[u.id])

    print(
        f"Manual check of rc -> route cost = {cost_sum}, duals = {dual_sum}, rc = {cost_sum - dual_sum}")


def check_route_reduced_cost_with_RCI(model, RCI_constrs, cover_constrs, customers, start_depot, end_depot, route):
    dist = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            dist[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    cost_sum = 0
    for (idx, u) in enumerate(route.visits[:-1]):
        v = route.visits[idx + 1]
        cost_sum += dist[u.id, v.id]

    cover_dual_sum = 0
    for u in route.visits[1:-1]:
        cover_dual_sum += model.getDual(cover_constrs[u.id])

    RCI_dual_sum = 0
    for (idx, u) in enumerate(route.visits[:-1]):
        v = route.visits[idx + 1]
        constrs = RCI_constrs[u.id] - RCI_constrs[v.id]
        for c in constrs:
            RCI_dual_sum += model.getDual(c)[0]

    print(f"Manual check of rc -> rc = {cost_sum - cover_dual_sum - RCI_dual_sum}, with RCI_dual = {RCI_dual_sum}")


def check_rc_from_matrix(model, route, x_ij, capacity, flow_constrs):
    flow_names = [flow_constrs[l][c].name for l in flow_constrs for c in flow_constrs[l]]
    # GET THE DUAL VECTOR PI_TRANSPOSE
    all_constrs = model.getConstraint()
    dual_values = [0] * len(all_constrs)
    dual_values_with_flow = [0] * len(all_constrs)
    counted_flow = 0
    for constr in all_constrs:
        dual_values_with_flow[constr.index] = model.getDual(constr)
        counted_flow += 1
        if constr.name not in flow_names:
            counted_flow -= 1
            dual_values[constr.index] = model.getDual(constr)

    print(f"We counted {counted_flow} flow constraints and left them as 0.")

    pi_transpose = np.array(dual_values)

    legs = []
    for idx, u in enumerate(route.visits[:-1]):
        legs.append((u.id, route.visits[idx + 1].id))


    max_l = max(l for l in x_ij)
    # GET INDICES OF COLUMNS CORRESPONDING TO EDGES DESCRIBED BY ROUTE
    cap_remain = str(round(capacity))
    column_indices = []
    continue_loop = True
    target_leg = 0
    while continue_loop:
        continue_loop = False
        for (i_name, j_name) in x_ij[max_l]:
            [u_id, i_cap] = i_name.split("_")
            [v_id, j_cap] = j_name.split("_")

            if (u_id, v_id) == legs[target_leg]:
                if i_cap == cap_remain:
                    column_indices.append(x_ij[max_l][i_name, j_name].index)
                    cap_remain = j_cap
                    if v_id != "end":
                        continue_loop = True
                        target_leg += 1
                    break

    # SUM THESE COLUMNS
    total_column = [0] * len(all_constrs)
    for constr in all_constrs:
        for col_idx in column_indices:
            total_column[constr.index] += model.getcoef(constr.index, col_idx)
    # for col_idx in column_indices:
        # total_column += model.getcols(col_idx)

    # CALCULATION
    rc = route.cost - sum(dual * a_val for dual, a_val in zip(pi_transpose, total_column))

    print(f"Reduced cost as calculated by matrix values: {rc}")



# def check_rc_jy(model, x_ij, route):