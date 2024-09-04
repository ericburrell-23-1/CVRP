import math
import xpress as xp
from models.data_structures.customer import Customer


def create_RMP_GM_model(omega_R_plus: list, customers: list, start_depot: Customer, end_depot: Customer):
    model = xp.problem("CG_GM_model")
    model.controls.outputlog = 0

    x = {}
    cost = distance_dict(customers, start_depot, end_depot)
    sorted_edges = {}
    nodes = {}
    all_l = []

    for (l, graph) in enumerate(omega_R_plus):
        all_l.append(l)
        sorted_edges[l] = sorted(graph[0], key=lambda E: (
            E[0].u.id, E[1].u.id, E[0].cap_remain))
        nodes[l] = graph[1]

        x[l] = {}

        # VARIABLES
        for (i, j) in sorted_edges[l]:
            new_var = model.addVariable(
                vartype=xp.continuous, lb=0, name=f"x_l{l}_{i.name}_{j.name}")
            x[l][i.name, j.name] = new_var

    # OBJECTIVE
    obj_terms = []
    for l in all_l:
        for (i, j) in sorted_edges[l]:
            obj_terms.append(x[l][i.name, j.name] * cost[i.u.id, j.u.id])

    model.setObjective(xp.Sum(obj_terms), xp.minimize)

    # CONSTRAINTS
    # COVER CONSTRAINTS
    cover_constrs = {}
    for u in customers:
        coverage = []
        for l in all_l:
            for (i, j) in sorted_edges[l]:
                if i.u == u:
                    coverage.append(x[l][i.name, j.name])

        constr = xp.Sum(coverage) >= 1
        constr.name = f"cover_{u.id}"
        model.addConstraint(constr)

        cover_constrs[u.id] = constr

    # FLOW CONSERVATION CONSTRAINTS
    for l in all_l:
        for node in nodes[l]:
            if node.u not in {start_depot, end_depot}:
                flow_in = []
                flow_out = []
                for (i, j) in sorted_edges[l]:
                    if i == node:
                        flow_out.append(x[l][i.name, j.name])

                    if j == node:
                        flow_in.append(x[l][i.name, j.name])

                constr = xp.Sum(flow_in) == xp.Sum(flow_out)
                constr.name = f"flow_l{l}_{node.name}"
                model.addConstraint(constr)

    return model, cover_constrs


def create_RMP_GM_ILP_model(omega_R_plus: list, customers: list, start_depot: Customer, end_depot: Customer):
    model = xp.problem("CG_GM_ILP_model")

    x = {}
    cost = distance_dict(customers, start_depot, end_depot)
    sorted_edges = {}
    nodes = {}
    all_l = []

    for (l, graph) in enumerate(omega_R_plus):
        all_l.append(l)
        sorted_edges[l] = sorted(graph[0], key=lambda E: (
            E[0].u.id, E[1].u.id, E[0].cap_remain))
        nodes[l] = graph[1]

        x[l] = {}

        # VARIABLES
        for (i, j) in sorted_edges[l]:
            new_var = model.addVariable(
                vartype=xp.binary, lb=0, name=f"x_l{l}_{i.name}_{j.name}")
            x[l][i.name, j.name] = new_var

    # OBJECTIVE
    obj_terms = []
    for l in all_l:
        for (i, j) in sorted_edges[l]:
            obj_terms.append(x[l][i.name, j.name] * cost[i.u.id, j.u.id])

    model.setObjective(xp.Sum(obj_terms), xp.minimize)

    # CONSTRAINTS
    # COVER CONSTRAINTS
    cover_constrs = {}
    for u in customers:
        coverage = []
        for l in all_l:
            for (i, j) in sorted_edges[l]:
                if i.u == u:
                    coverage.append(x[l][i.name, j.name])

        constr = xp.Sum(coverage) >= 1
        constr.name = f"cover_{u.id}"
        model.addConstraint(constr)

        cover_constrs[u.id] = constr

    # FLOW CONSERVATION CONSTRAINTS
    for l in all_l:
        for node in nodes[l]:
            if node.u not in {start_depot, end_depot}:
                flow_in = []
                flow_out = []
                for (i, j) in sorted_edges[l]:
                    if i == node:
                        flow_out.append(x[l][i.name, j.name])

                    if j == node:
                        flow_in.append(x[l][i.name, j.name])

                constr = xp.Sum(flow_in) == xp.Sum(flow_out)
                constr.name = f"flow_l{l}_{node.name}"
                model.addConstraint(constr)

    return model


def distance_dict(customers: list, start_depot: Customer, end_depot: Customer):
    cost = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            cost[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    return cost
