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
        edge_weight = dist(start_depot, u) - dual(model, u)
        g.add_edge("Source", str(u.id), res_cost=array([
                   float(u.demand)]), weight=edge_weight)
        # print(
        #     f"Demand: {0}, Weight: {dist(start_depot, u) - dual(model, u)} dist: {dist(start_depot, u)} dual: {dual(model, u)}")
        edge_weight = dist(start_depot, u)
        g.add_edge(str(u.id), "Sink", res_cost=array(
            [0.0]), weight=edge_weight)

    # CONNECT CUSTOMERS TO EACH OTHER
    for u in customers:
        for v in customers:
            if u != v:
                edge_weight = dist(u, v) - dual(model, v)
                # print(f"Edge weight: {edge_weight}")
                # print(f"Demand: {v.demand}")
                g.add_edge(str(u.id), str(v.id), res_cost=array([
                           float(v.demand)]), weight=edge_weight)

    # DEFINE RESOURCE CONSTRAINTS
    max_res, min_res = array([capacity + 1]), array([0.0])

    # RUN LABELING ALG TO GET PATH
    bidirec = BiDirectional(g, max_res=max_res, min_res=min_res,
                            direction="both", elementary=True)

    bidirec.run()
    print(f"New path = {bidirec.path}")

    return bidirec.path, bidirec.total_cost


def dist(a: Customer, b: Customer):
    return math.hypot((a.x - b.x), (a.y - b.y))


def dual(model: Model, customer: Customer):
    return model.getConstrByName(f"cover_{customer.id}").Pi


def column_gen(model, customers, start_depot, end_depot, cap):
    cust_by_id = {}
    for u in customers:
        cust_by_id[u.id] = u
    # BUILD PRICING GRAPH
    pricing_graph = DiGraph(directed=True, n_res=1)

    for u in customers:
        pricing_graph.add_edge("Source", u, res_cost=array(
            [u.demand]), weight=dist(start_depot, u))
        pricing_graph.add_edge(u, "Sink", res_cost=array(
            [0]), weight=dist(start_depot, u) - dual(model, u))

        for v in customers:
            if v.id != u.id:
                pricing_graph.add_edge(u, v, res_cost=array(
                    [v.demand]), weight=dist(u, v) - dual(model, v))

    bidirec = BiDirectional(pricing_graph, [float(cap)], [
                            0.0], elementary=True, direction="both")

    bidirec.run()
    print(f"Graph Solved: {bidirec.path}")

    visited_cust = bidirec.path[1:-1]
    visited_cust.insert(0, start_depot)
    visited_cust.append(end_depot)

    new_route = Route(visited_cust, customers, start_depot, end_depot)

    return new_route, bidirec.total_cost
