import math
import xpress as xp
from models.data_structures.customer import Customer


def create_RMP_GM_LA_model(omega_R_plus: list, customers: list, start_depot: Customer, end_depot: Customer):
    """
    Creates LP-relaxed xpress model using GraphMaster approach without LA Arcs. Returns the model and cover constraints
    """

    model = xp.problem("GM_no_LA_model")
    model.controls.outputlog = 0

    # print(
    #     f"Creating RMP_LA model with {len(omega_R_plus)} graphs and {len(omega_y_l)} sets of LA arcs.")

    x_ij = {}
    cost = distance_dict(customers, start_depot, end_depot)
    sorted_edges = {}
    nodes = {}
    all_l = []

    for (l, graph) in enumerate(omega_R_plus):
        # print(f"Going through graph {l}")
        all_l.append(l)
        sorted_edges[l] = sorted(graph[0], key=lambda E: (
            E[0].u.id, E[1].u.id, E[0].cap_remain))
        nodes[l] = graph[1]

        x_ij[l] = {}

        # VARIABLES
        # GRAPH VARIABLES
        for (i, j) in sorted_edges[l]:
            x_ij[l][i.name, j.name] = model.addVariable(
                vartype=xp.continuous, lb=0, name=f"xij_l{l}_{i.name}_{j.name}")

    # OBJECTIVE
    obj_terms = []
    for l in all_l:
        for (i, j) in sorted_edges[l]:
            coef = cost[i.u.id, j.u.id]
            obj_terms.append(coef * x_ij[l][i.name, j.name])




    model.setObjective(xp.Sum(obj_terms), xp.minimize)

    # CONSTRAINTS
    # COVER CONSTRAINTS
    cover_constrs = {}
    for u in customers:
        coverage = []
        for l in all_l:
            for (i, j) in sorted_edges[l]:
                if i.u.id == u.id:
                    coverage.append(x_ij[l][i.name, j.name])

        constr = xp.Sum(coverage) >= 1
        constr.name = f"cover_{u.id}"
        model.addConstraint(constr)

        cover_constrs[u.id] = constr

    # FLOW CONSTRAINTS
    flow_constrs = {}
    for l in all_l:
        flow_constrs[l] = {}
        for node in nodes[l]:
            if node.u not in {start_depot, end_depot}:
                flow_in = []
                flow_out = []
                for (i, j) in sorted_edges[l]:
                    if i == node:
                        flow_out.append(x_ij[l][i.name, j.name])

                    if j == node:
                        flow_in.append(x_ij[l][i.name, j.name])

                constr = xp.Sum(flow_in) - xp.Sum(flow_out) == 0
                constr.name = f"flow_l{l}_{node.name}"
                model.addConstraint(constr)

                flow_constrs[l][node.name] = constr


    return model, cover_constrs, flow_constrs, x_ij


def distance_dict(customers: list, start_depot: Customer, end_depot: Customer):
    cost = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            cost[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    return cost


def convert_to_ILP(model: xp.problem):
    variables = model.getVariable()

    for var in variables:
        var.vartype = xp.binary