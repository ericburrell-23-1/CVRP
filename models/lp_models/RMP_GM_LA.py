import math
import xpress as xp
from models.data_structures.customer import Customer


def create_RMP_GM_LA_model(omega_R_plus: list, omega_y_l: list, customers: list, start_depot: Customer, end_depot: Customer):
    """
    Creates LP-relaxed xpress model using GraphMaster approach with LA Arcs. Returns the model and cover constraints

    Accepts a list of graphs omega_R_plus of the form (edges, nodes), and associated LA Arcs omega_y_l, as a list of dictionaries keyed by y = (u, v, d).  Lenth of omega_r_plus and omega_y_l should be the same.
    """

    model = xp.problem("GM_LA_model")
    model.controls.outputlog = 0

    print(
        f"Creating RMP_LA model with {len(omega_R_plus)} graphs and {len(omega_y_l)} sets of LA arcs.")

    x_ij = {}
    x_p = {}
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
        x_p[l] = {}

        # VARIABLES
        # GRAPH VARIABLES
        for (i, j) in sorted_edges[l]:
            x_ij[l][i.name, j.name] = model.addVariable(
                vartype=xp.continuous, lb=0, name=f"xij_l{l}_{i.name}_{j.name}")

        # LA ARC VARIABLES
        omega_y = omega_y_l[l]
        for y in omega_y:
            for arc in omega_y[y]:
                x_p[l][arc.id] = model.addVariable(
                    vartype=xp.continuous, lb=0, name=f"xp_l{l}_{arc.id}")

    # OBJECTIVE
    depart_depot_obj_terms = []
    depart_depot_vars = {}
    arcs_obj_terms = []

    for l in all_l:
        if len(nodes[l]):
            start_node = nodes[l][0]
            for u in customers:
                for j in nodes[l]:
                    if j.u.id == u.id and int(j.cap_remain) == int(round(start_node.cap_remain)):
                        depart_depot_obj_terms.append(
                            x_ij[l][start_node.name, j.name] * cost[start_node.u.id, u.id])
                        if u.id in depart_depot_vars:
                            depart_depot_vars[u.id].append(
                                x_ij[l][start_node.name, j.name])
                        else:
                            depart_depot_vars[u.id] = [
                                x_ij[l][start_node.name, j.name]]

            omega_y = omega_y_l[l]
            for y in omega_y:
                for arc in omega_y[y]:
                    arcs_obj_terms.append(x_p[l][arc.id] * arc.cost)

    all_obj_terms = depart_depot_obj_terms + arcs_obj_terms
    model.setObjective(xp.Sum(all_obj_terms), xp.minimize)

    # CONSTRAINTS
    # COVER CONSTRAINTS
    cover_constrs = {}
    for u in customers:
        coverage = []
        if u.id in depart_depot_vars:
            for var in depart_depot_vars[u.id]:
                coverage.append(var)
        for l in all_l:
            omega_y = omega_y_l[l]
            for y in omega_y:
                for arc in omega_y[y]:
                    if u in arc.visits[1:]:
                        coverage.append(x_p[l][arc.id])

        constr = xp.Sum(coverage) >= 1
        constr.name = f"cover_{u.id}"
        model.addConstraint(constr)

        cover_constrs[u.id] = constr

    # FLOW CONSTRAINTS
    for l in all_l:
        for node in nodes[l]:
            if node.u not in {start_depot, end_depot}:
                flow_in = []
                flow_out = []
                for (i, j) in sorted_edges[l]:
                    if i == node:
                        flow_out.append(x_ij[l][i.name, j.name])

                    if j == node:
                        flow_in.append(x_ij[l][i.name, j.name])

                constr = xp.Sum(flow_in) == xp.Sum(flow_out)
                constr.name = f"flow_l{l}_{node.name}"
                model.addConstraint(constr)

    # GRAPH/ARC CONSISTENCY CONSTRAINTS
    for l in all_l:
        omega_y = omega_y_l[l]
        for (u_id, v_id, d) in omega_y:
            arc_terms = []
            graph_terms = []

            for arc in omega_y[(u_id, v_id, d)]:
                arc_terms.append(x_p[l][arc.id])

            for (i, j) in sorted_edges[l]:
                if i.u.id == u_id and j.u.id == v_id and int(j.cap_remain) == int(round(i.cap_remain - d)):
                    graph_terms.append(x_ij[l][i.name, j.name])

            constr = xp.Sum(arc_terms) == xp.Sum(graph_terms)
            constr.name = f"consistent_l{l}_y{u_id}_{v_id}_{d}"
            model.addConstraint(constr)

    return model, cover_constrs, x_ij, x_p


def distance_dict(customers: list, start_depot: Customer, end_depot: Customer):
    cost = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            cost[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    return cost
