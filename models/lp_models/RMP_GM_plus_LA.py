import math
from gurobipy import Model, GRB, quicksum
from models.data_structures.customer import Customer


def create_RMP_GM_LA_model(omega_R_plus: list, omega_y_l: list, customers: list, start_depot: Customer, end_depot: Customer):
    """
    Creates Gurobi model using GraphMaster approach with LA Arcs. 

    Accepts a list of graphs omega_R_plus of the form (edges, nodes), and associated LA Arcs omega_y_l, as a list of dictionaries keyed by y = (u, v, d).  Lenth of omega_r_plus and omega_y_l should be the same.
    """
    print(f"Creating new model with l = {len(omega_R_plus)}")
    model = Model("GM_LA_MODEL")
    # model.setParam('OutputFlag', 0)

    x_ij = {}
    x_p = {}
    cost = distance_dict(customers, start_depot, end_depot)
    sorted_edges = {}
    nodes = {}
    all_l = []

    for (l, graph) in enumerate(omega_R_plus):
        all_l.append(l)
        sorted_edges[l] = sorted(graph[0], key=lambda E: (
            E[0].u.id, E[1].u.id, E[0].cap_remain))
        nodes[l] = graph[1]

        x_ij[l] = {}
        x_p[l] = {}

        # VARIABLES
        for (i, j) in sorted_edges[l]:
            x_ij[l][i.name, j.name] = model.addVar(
                vtype=GRB.CONTINUOUS, lb=0, name=f"x_{i.name}_{j.name}")

        omega_y = omega_y_l[l]
        for y in omega_y:
            for arc in omega_y[y]:
                x_p[l][arc] = model.addVar(
                    vtype=GRB.CONTINUOUS, name=f"x_p_{arc.id}")

    model.update()

    # OBJECTIVE
    start_obj = []
    arcs_obj = []
    for l in all_l:
        start_node = nodes[l][0]
        for u in customers:
            start_obj.extend([x_ij[l][start_node.name, j.name] *
                             cost[start_node.u.id, u.id] for j in nodes[l] if j.u.id == u.id and j.cap_remain == start_node.cap_remain - u.demand])

        omega_y = omega_y_l[l]
        for y in omega_y:
            for arc in omega_y[y]:
                arcs_obj.append(x_p[l][arc] * arc.cost)

    model.setObjective(
        quicksum(start_obj) + quicksum(arcs_obj)
    )

    # CONSTRAINTS
    # COVER CONSTRAINTS
    for u in customers:
        coverage = []
        for l in all_l:
            omega_y = omega_y_l[l]
            for y in omega_y:
                for arc in omega_y[y]:
                    if u in arc.visits:
                        coverage.append(x_p[l][arc])

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
                        flow_out.append(x_ij[l][i.name, j.name])

                for (i, j) in sorted_edges[l]:
                    if j == node:
                        flow_in.append(x_ij[l][i.name, j.name])

                model.addConstr(
                    quicksum(flow_in) == quicksum(flow_out),
                    name=f"flow_l{l}_{node.name}"
                )

    # p consistent with ij
    for l in all_l:
        omega_y = omega_y_l[l]
        for (u_id, v_id, d) in omega_y:
            arc_terms = []
            ij_terms = []

            for arc in omega_y[(u_id, v_id, d)]:
                arc_terms.append(x_p[l][arc])

            for (i, j) in sorted_edges[l]:
                if i.u.id == u_id and j.u.id == v_id and (j.cap_remain == i.cap_remain - d):
                    ij_terms.append(x_ij[l][i.name, j.name])

            model.addConstr(quicksum(arc_terms) == quicksum(
                ij_terms), name=f"arc_consistency_{l}_({u_id}_{v_id}_{d})")

    return model


def distance_dict(customers: list, start_depot: Customer, end_depot: Customer):
    cost = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            cost[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    return cost
