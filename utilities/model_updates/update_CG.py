import gurobipy as gp
import xpress as xp
from gurobipy import Model, GRB
from models.data_structures.route import Route


def add_col_to_model_gurobi(model: Model, route: Route, customers: list):

    a_coeffs = []
    constrs = []

    for u in customers:
        a_coeffs.append(route.a_ul[u.id])
        constrs.append(model.getConstrByName(f"cover_{u.id}"))

    new_col = gp.Column(a_coeffs, constrs)
    model.addVar(column=new_col, obj=route.cost, vtype=GRB.CONTINUOUS,
                 name=f"theta_{route.id}")

    model.update()

    return model


def add_col_to_model(model: xp.problem, constraints: dict, route: Route, customers: list):
    row_coeffs = []
    row_indices = []
    for u in customers:
        row_coeffs.append(route.a_ul[u.id])
        row_indices.append(constraints[u.id].index)

    model.addcols(
        objcoef=[route.cost],
        start=[0, len(row_coeffs)],
        rowind=row_indices,
        rowcoef=row_coeffs,
        lb=[0],
        ub=[xp.infinity],
        names=[f"theta_{route.id}"],
        types=['C']
    )
