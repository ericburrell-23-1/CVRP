import math
from cspy import BiDirectional
from networkx import DiGraph
from numpy import array
from gurobipy import Model
from models.data_structures.customer import Customer
from models.data_structures.route import Route


def generate_col(model: Model, customers: list, start_depot: Customer, end_depot: Customer, capacity: int):
    visits_by_id, reduced_cost = pricing(
        model, customers, start_depot, capacity)

    # print("Path found. Building Route")

    cust_by_id = {}
    for u in customers:
        cust_by_id[u.id] = u

    visits = []
    for id in visits_by_id:
        if id == "Source":
            visits.append(start_depot)
        elif id == "Sink":
            visits.append(end_depot)
        else:
            visits.append(cust_by_id[id])

    new_route = Route(visits, customers, start_depot, end_depot)

    # print("Route created. Returning")

    return new_route, reduced_cost


def pricing(model: Model, customers: list, start_depot: Customer, capacity: int):
    # CREATE GRAPH
    g = DiGraph(directed=True, n_res=1)

    # CONNECT EACH CUSTOMER TO SOURCE/SINK
    for u in customers:
        # print(f"Demand: {u.demand}, Weight: {dist(start_depot, u)}")
        g.add_edge("Source", str(u.id), res_cost=array([
                   u.demand]), weight=dist(start_depot, u))
        # print(
        #     f"Demand: {0}, Weight: {dist(start_depot, u) - dual(model, u)} dist: {dist(start_depot, u)} dual: {dual(model, u)}")
        g.add_edge(str(u.id), "Sink", res_cost=array([0]), weight=(
            dist(start_depot, u) - dual(model, u)))

    # CONNECT CUSTOMERS TO EACH OTHER
    for u in customers:
        for v in customers:
            if u != v:
                edge_weight = dist(u, v) - dual(model, u)
                # print(f"Edge weight: {edge_weight}")
                # print(f"Demand: {v.demand}")
                g.add_edge(str(u.id), str(v.id), res_cost=array([
                           v.demand]), weight=edge_weight)

    # DEFINE RESOURCE CONSTRAINTS
    max_res, min_res = [capacity], [0]

    # RUN LABELING ALG TO GET PATH
    bidirec = BiDirectional(g, max_res, min_res,
                            direction="both", elementary=True)
    print("BiDirec created")

    bidirec.run()
    print(f"Done solving. Path = {bidirec.path}")

    return bidirec.path, bidirec.total_cost


def dist(a: Customer, b: Customer):
    return math.hypot(a.x - b.x, a.y - b.y)


def dual(model: Model, customer: Customer):
    dual_val = model.getConstrByName(f"customer_visted_once_{customer.id}").Pi
    # NEED TO CALCULATE THE DUAL
    return dual_val