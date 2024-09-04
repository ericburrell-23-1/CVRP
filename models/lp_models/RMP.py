import xpress as xp


def create_RMP_model(omega_R, customers):
    model = xp.problem("CG_MODEL")
    model.controls.outputlog = 0

    # VARIABLES
    theta = {}
    for l in omega_R:
        theta[l.id] = model.addVariable(
            name=f"theta_{l.id}", vartype=xp.continuous, lb=0)

    # OBJECTIVE
    model.setObjective(xp.Sum(l.cost * theta[l.id]
                       for l in omega_R), sense=xp.minimize)

    # CONSTRAINTS
    cover_constrs = {}

    for u in customers:
        constr = xp.Sum(l.a_ul[u.id] * theta[l.id] for l in omega_R) >= 1
        constr.name = f"cover_{u.id}"
        model.addConstraint(constr)

        cover_constrs[u.id] = constr

    return model, cover_constrs


def create_RMP_ILP_model(omega_R, customers):
    model = xp.problem("CG_MODEL")

    # VARIABLES
    theta = {}
    for l in omega_R:
        theta[l.id] = model.addVariable(
            name=f"theta_{l.id}", vartype=xp.binary, lb=0)

    # OBJECTIVE
    model.setObjective(xp.Sum(l.cost * theta[l.id]
                       for l in omega_R), sense=xp.minimize)

    # CONSTRAINTS
    for u in customers:
        constr = xp.Sum(l.a_ul[u.id] * theta[l.id] for l in omega_R) >= 1
        constr.name = f"cover_{u.id}"
        model.addConstraint(constr)

    return model
