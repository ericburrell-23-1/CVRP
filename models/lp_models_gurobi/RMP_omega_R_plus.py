import math
from models.data_structures.customer import Customer
from gurobipy import Model, GRB, quicksum


def create_RMP_GM_model(omega_R_plus: list, customers: list, start_depot: Customer, end_depot: Customer):
    print(f"Creating new model with l = {len(omega_R_plus)}")
    model = Model("CG_Omega_plus_MODEL")
    model.setParam('OutputFlag', 0)

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
            new_var = model.addVar(
                vtype=GRB.CONTINUOUS, lb=0, name=f"x_{i.name}_{j.name}")
            x[l][i.name, j.name] = new_var

    model.update()

    # OBJECTIVE
    obj = []
    for l in all_l:
        for (i, j) in sorted_edges[l]:
            obj.append(x[l][i.name, j.name] * cost[i.u.id, j.u.id])

    model.setObjective(
        quicksum(obj), GRB.MINIMIZE
    )

    # CONSTRAINTS
    # COVER CONSTRAINTS
    for u in customers:
        coverage = []
        for l in all_l:
            for (i, j) in sorted_edges[l]:
                if i.u == u:
                    coverage.append(x[l][i.name, j.name])

        model.addConstr(
            quicksum(coverage) >= 1,
            name=f"cover_{u.id}"
        )

    # FLOW CONSTRAINTS
    for l in all_l:
        for node in nodes[l]:
            if node.u not in {start_depot, end_depot}:
                flow_in = []
                flow_out = []
                for (i, j) in sorted_edges[l]:
                    if i == node:
                        flow_out.append(x[l][i.name, j.name])

                for (i, j) in sorted_edges[l]:
                    if j == node:
                        flow_in.append(x[l][i.name, j.name])

                model.addConstr(
                    quicksum(flow_in) == quicksum(flow_out),
                    name=f"flow_l{l}_{node.name}"
                )

    for l in all_l:
        departing_depot = []
        returning_depot = []
        for (i, j) in sorted_edges[l]:
            if i.u == start_depot:
                departing_depot.append(x[l][i.name, j.name])
        for (i, j) in sorted_edges[l]:
            if j.u == end_depot:
                returning_depot.append(x[l][i.name, j.name])
        model.addConstr(
            quicksum(departing_depot) == quicksum(returning_depot), name=f"flow_l{l}_depot"
        )

    return model


def create_RMP_GM_ILP_model(omega_R_plus: list, customers: list, start_depot: Customer, end_depot: Customer):
    model = Model("CG_Omega_plus_MODEL")

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
            new_var = model.addVar(
                vtype=GRB.BINARY, lb=0, name=f"x_{i.name}_{j.name}")
            x[l][i.name, j.name] = new_var

    model.update()

    # OBJECTIVE
    obj = []
    for l in all_l:
        for (i, j) in sorted_edges[l]:
            obj.append(x[l][i.name, j.name] * cost[i.u.id, j.u.id])

    model.setObjective(
        quicksum(obj), GRB.MINIMIZE
    )

    # CONSTRAINTS
    # COVER CONSTRAINTS
    for u in customers:
        coverage = []
        for l in all_l:
            for (i, j) in sorted_edges[l]:
                if i.u == u:
                    coverage.append(x[l][i.name, j.name])

        model.addConstr(
            quicksum(coverage) >= 1,
            name=f"cover_{u.id}"
        )

    # FLOW CONSTRAINTS
    for l in all_l:
        for node in nodes[l]:
            if node.u not in {start_depot, end_depot}:
                flow_in = []
                flow_out = []
                for (i, j) in sorted_edges[l]:
                    if i == node:
                        flow_out.append(x[l][i.name, j.name])

                for (i, j) in sorted_edges[l]:
                    if j == node:
                        flow_in.append(x[l][i.name, j.name])

                model.addConstr(
                    quicksum(flow_in) == quicksum(flow_out),
                    name=f"flow_l{l}_{node.name}"
                )

    for l in all_l:
        departing_depot = []
        returning_depot = []
        for (i, j) in sorted_edges[l]:
            if i.u == start_depot:
                departing_depot.append(x[l][i.name, j.name])
        for (i, j) in sorted_edges[l]:
            if j.u == end_depot:
                returning_depot.append(x[l][i.name, j.name])
        model.addConstr(
            quicksum(departing_depot) == quicksum(returning_depot), name=f"flow_l{l}_depot"
        )

    return model


def distance_dict(customers: list, start_depot: Customer, end_depot: Customer):
    cost = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            cost[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    return cost
