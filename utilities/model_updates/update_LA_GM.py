import math
import xpress as xp

def add_family_to_model(model: xp.problem, omega_R_plus: list, omega_y_l: list, cover_constrs: dict, flow_constrs: dict, x_ij: dict, x_p: dict):
    # GET THE INDEX OF THE FIRST FAMILY NOT PRESENT IN THE CURRENT MODEL
    start_index = len(flow_constrs)

    # BEGIN ADDING FAMILIES TO MODEL
    for l, graph in enumerate(omega_R_plus[start_index:]):
        graph_index = int(round(l + start_index))
        # START WITH ADDING COLUMNS
        # DEFINE NEW COLUMN VALUES AS LISTS
        obj_coeffs = []
        row_indices = []
        row_coeffs = []
        names = []
        lbs = []
        ubs = []
        starts = [0]
        types = []

        # STORE COLUMN INDICIES TO RETRIEVE VARIABLES LATER
        col_index = {}
        last_col_index = model.getVariable()[-1].index

        # ADD EDGE COLUMNS
        sorted_edges = sorted(graph[0], key=lambda E: (
            E[0].u.id, E[1].u.id, E[0].cap_remain))
        nodes = graph[1]
        start_node = nodes[0]

        for (i, j) in sorted_edges:
            edge_row_indices = []
            edge_row_coeffs = []
            obj_coef = 0

            if i.name == start_node.name:
                edge_row_indices.append(cover_constrs[j.u.id].index)
                edge_row_coeffs.append(1)
                obj_coef = math.hypot(i.u.x - j.u.x, i.u.y - j.u.y)

            row_indices.extend(edge_row_indices)
            row_coeffs.extend(edge_row_coeffs)
            starts.append(starts[-1] + len(edge_row_coeffs))
            obj_coeffs.append(obj_coef)
            names.append(f"xij_l{graph_index}_{i.name}_{j.name}")
            lbs.append(0)
            ubs.append(xp.infinity)
            types.append('C')

            last_col_index += 1
            col_index[f"xij_l{graph_index}_{i.name}_{j.name}"] = last_col_index

        # ADD ARC COLUMNS
        omega_y = omega_y_l[graph_index]
        for y in omega_y:
            for arc in omega_y[y]:
                arc_row_indices = []
                arc_row_coeffs = []

                # ADD COEFFICIENTS ASSOCIATED WITH COVERAGE CONSTRAINTS
                for u in arc.visits[1:]:
                    if u.id != "end":
                        arc_row_indices.append(cover_constrs[u.id].index)
                        arc_row_coeffs.append(1)

                row_indices.extend(arc_row_indices)
                row_coeffs.extend(arc_row_coeffs)
                starts.append(starts[-1] + len(arc_row_coeffs))
                obj_coeffs.append(arc.cost)
                names.append(f"xp_l{graph_index}_{arc.id}")
                lbs.append(0)
                ubs.append(xp.infinity)
                types.append('C')

                last_col_index += 1
                col_index[f"xp_l{graph_index}_{arc.id}"] = last_col_index


        # ADD COLUMNS TO MODEL
        model.addcols(
            objcoef=obj_coeffs,
            start=starts,
            rowind=row_indices,
            rowcoef=row_coeffs,
            lb=lbs,
            ub=ubs,
            names=names,
            types=types
        )

        # ADD VARS TO VAR DICTIONARIES
        x_ij[graph_index] = {}
        for (i, j) in sorted_edges:
            x_ij[graph_index][i.name, j.name] = model.getVariable(col_index[f"xij_l{graph_index}_{i.name}_{j.name}"])

        x_p[graph_index] = {}
        for y in omega_y:
            for arc in omega_y[y]:
                    x_p[graph_index][arc.id] = model.getVariable(col_index[f"xp_l{graph_index}_{arc.id}"])

        # ADD FLOW CONSTRAINTS FOR NEW NODES
        flow_constrs[graph_index] = {}
        for node in nodes:
            if node.u.id not in {"start", "end"}:
                flow_in = []
                flow_out = []
                for (i, j) in sorted_edges:
                    if i == node:
                        flow_out.append(x_ij[graph_index][i.name, j.name])

                    if j == node:
                        flow_in.append(x_ij[graph_index][i.name, j.name])

                constr = xp.Sum(flow_in) - xp.Sum(flow_out) == 0
                constr.name = f"flow_l{graph_index}_{node.name}"
                model.addConstraint(constr)

                flow_constrs[graph_index][node.name] = constr

        # ADD NEW ARC/EDGE CONSISTENCY CONSTRAINTS
        for (u_id, v_id, d) in omega_y:
            arc_terms = []
            graph_terms = []

            for arc in omega_y[(u_id, v_id, d)]:
                arc_terms.append(x_p[graph_index][arc.id])

            for (i, j) in sorted_edges:
                if i.u.id == u_id and j.u.id == v_id and int(j.cap_remain) == int(round(i.cap_remain - d)):
                    graph_terms.append(x_ij[graph_index][i.name, j.name])

            constr = xp.Sum(arc_terms) - xp.Sum(graph_terms) == 0
            constr.name = f"consistent_l{graph_index}_y{u_id}_{v_id}_{d}"
            model.addConstraint(constr)

    # print(f"Adding {len(new_RCIs)} new RCI constraints")
    # for RCI_constr in new_RCIs:
    #     constr = xp.Sum(RCI_constr[0]) >= (RCI_constr[1])
    #     constr.name = f"RCI_{RCI_constr[2].name}"
    #     model.addConstraint(constr)
    #     # ADD CONSTR TO RCI_CONSTR DICT FOR ALL CUST IN N_HAT
    #     for u in RCI_constr[2].N_hat:
    #         RCI_constrs[u.id].add(constr.name)
    #     # RCI_constrs[constr.name] = RCI_constr[2].N_hat


def add_RCI_constrs(model: xp.problem, new_RCIs: list, RCI_constrs: dict):
    print(f"Adding {len(new_RCIs)} new RCI constraints")
    for RCI_constr in new_RCIs:
        constr = xp.Sum(RCI_constr[0]) >= (RCI_constr[1])
        constr.name = f"RCI_{RCI_constr[2].name}"
        model.addConstraint(constr)
        # ADD CONSTR TO RCI_CONSTR DICT FOR ALL CUST IN N_HAT
        for u in RCI_constr[2].N_hat:
            RCI_constrs[u.id].add((constr.name, RCI_constr[1]))
        # RCI_constrs[constr.name] = RCI_constr[2].N_hat