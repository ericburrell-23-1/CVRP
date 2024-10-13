import math
import xpress as xp

def update_model(model: xp.problem, new_arcs: list, new_edges: list, new_nodes: list, cover_constrs: dict, flow_constrs: dict, x_ij: dict, x_p: dict, RCI_constrs: dict):
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


    # ADD NEW FLOW CONSTRAINTS FOR NEW NODES
    constr_added = 0 
    for l, nodes in enumerate(new_nodes):
        for node in nodes:
            flow_in = []
            flow_out = []

            constr = xp.Sum(flow_in) - xp.Sum(flow_out) == 0
            constr.name = f"flow_l{l}_{node.name}"
            model.addConstraint(constr)
            constr_added += 1

            flow_constrs[l][node.name] = constr

    print(f"Added {constr_added} flow constraints")

    # ADD COLUMNS FOR NEW EDGES
    for l, edges in enumerate(new_edges):
        for (i, j) in edges:
            edge_row_indices = []
            edge_row_coeffs = []

            edge_row_indices.append(flow_constrs[l][i.name].index)
            edge_row_coeffs.append(-1) 

            edge_row_indices.append(flow_constrs[l][j.name].index)
            edge_row_coeffs.append(1)

            if RCI_constrs != {}:
                for RCI_constr in RCI_constrs[i.u.id] - RCI_constrs[j.u.id]:
                    edge_row_indices.append(RCI_constr[0])
                    edge_row_coeffs.append(1)

            row_indices.extend(edge_row_indices)
            row_coeffs.extend(edge_row_coeffs)
            starts.append(starts[-1] + len(edge_row_coeffs))
            obj_coeffs.append(0)
            names.append(f"xij_l{l}_{i.name}_{j.name}")
            lbs.append(0)
            ubs.append(xp.infinity)
            types.append('C')

            last_col_index += 1
            col_index[f"xij_l{l}_{i.name}_{j.name}"] = last_col_index


    
    # ADD COLUMNS FOR NEW ARCS
    for l, omega_y in enumerate(new_arcs):
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
                names.append(f"xp_l{l}_{arc.id}")
                lbs.append(0)
                ubs.append(xp.infinity)
                types.append('C')

                last_col_index += 1
                col_index[f"xp_l{l}_{arc.id}"] = last_col_index

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

    # ADD NEW ARC/EDGE CONSISTENCY CONSTRAINTS
    for l, omega_y in enumerate(new_arcs):
        for (i, j) in new_edges[l]:
            x_ij[l][i.name, j.name] = model.getVariable(col_index[f"xij_l{l}_{i.name}_{j.name}"])

        for (u_id, v_id, d) in omega_y:
            arc_terms = []
            graph_terms = []

            for arc in omega_y[(u_id, v_id, d)]:
                x_p[l][arc.id] = model.getVariable(col_index[f"xp_l{l}_{arc.id}"])
                arc_terms.append(x_p[l][arc.id])

            for (i, j) in new_edges[l]:
                if i.u.id == u_id and j.u.id == v_id and int(j.cap_remain) == int(round(i.cap_remain - d)):
                    graph_terms.append(x_ij[l][i.name, j.name])

            constr = xp.Sum(arc_terms) - xp.Sum(graph_terms) == 0
            constr.name = f"consistent_l{l}_y{u_id}_{v_id}_{d}"
            model.addConstraint(constr)
