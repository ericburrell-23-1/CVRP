import xpress as xp

def build_RMP(opt):
    rmp = xp.problem("jy_opt_RMP")
    rmp.controls.outputlog = 0

    vars = {}
    constrs = {}
    constrs["RCI"] = {}

    # VARIABLES AND OBJECTIVE
    obj_terms = []
    for var_name in opt.objective:
        # print(f"Creating variable {var_name}. Obj coeff: {opt.objective[var_name]}")
        new_var = rmp.addVariable(vartype=xp.continuous, lb=0, name=str(var_name))
        obj_terms.append(new_var * opt.objective[var_name])
        vars[var_name] = new_var

    rmp.setObjective(xp.Sum(obj_terms), xp.minimize)

    # CONSTRAINTS
    constraint_terms = {}
    for con_name in opt.RHS:
        # print(f"Looking at RHS term {con_name}")
        constraint_terms[con_name] = []

    for edge_var, coeff in opt.edge_con_name_2_val.items():
        # print(f"\tEdge var: {edge_var[1]}, constr name: {edge_var[0]}, coeff: {coeff}")
        con_name = edge_var[0]
        var_name = edge_var[1]
        if con_name in constraint_terms:
            constraint_terms[con_name].append(vars[var_name] * coeff)

    # print(f"Found constraint terms: {constraint_terms} and RHS: {opt.RHS[con_name]}")
    for con_name in constraint_terms:
        if con_name[0] == 'Flow':
            new_constr = xp.Sum(constraint_terms[con_name]) == opt.RHS[con_name]
        else:
            new_constr = xp.Sum(constraint_terms[con_name]) >= opt.RHS[con_name]
        new_constr.name=str(con_name)
        rmp.addConstraint(new_constr)

        if con_name[0] == "RCI":
            update_RCI_dict(opt, con_name[1], new_constr, constrs)
        else:
            constrs[con_name] = new_constr

    return rmp, vars, constrs





def update_RCI_dict(opt, N_hat, RCI_constr, constrs):
    for u in N_hat:
        for v in set(opt.N + [-1]) - set(N_hat):
            if (u, v) not in constrs["RCI"]:
                constrs["RCI"][u, v] = [RCI_constr]
            else:
                constrs["RCI"][u, v].append(RCI_constr)