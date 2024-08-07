from gurobipy import Model, GRB, quicksum


def create_RMP_model(omega_R, customers):
    model = Model("CG_MODEL")
    model.setParam('OutputFlag', 0)

    # VARIABLES
    theta = {}
    for l in omega_R:
        theta[l.id] = model.addVar(vtype=GRB.CONTINUOUS, name=f"theta_{l.id}")

    # OBJECTIVE
    model.setObjective(
        quicksum((l.cost * theta[l.id]) for l in omega_R), GRB.MINIMIZE)

    # CONSTRAINTS
    for u in customers:
        model.addConstr(quicksum((l.a_ul[u.id] * theta[l.id])
                        for l in omega_R) >= 1, name=f"customer_visted_once_{u.id}")

    return model
