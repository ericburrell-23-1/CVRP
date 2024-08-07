import gurobipy as gp
from gurobipy import Model, GRB
from models.data_structures.route import Route


def add_col_to_model(model: Model, route: Route, customers: list):

    a_coeffs = []
    for u in customers:
        a_coeffs.append(route.a_ul[u.id])

    new_col = gp.Column(a_coeffs, model.getConstrs())
    model.addVar(column=new_col, obj=route.cost, vtype=GRB.CONTINUOUS,
                 name=f"theta_{route.id}")

    model.update()

    return model
