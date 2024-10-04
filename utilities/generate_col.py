import math
from cspy import BiDirectional
from networkx import DiGraph
from numpy import array
from models.data_structures.customer import Customer
from models.data_structures.route import Route


def generate_col(model, constraints: dict, customers: list, start_depot: Customer, end_depot: Customer, capacity: int, RCI_constrs: dict = None):
    duals = dual_dict(model, constraints, customers)

    visits_by_id, reduced_cost = pricing(model,
        duals, customers, start_depot, capacity, RCI_constrs)

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


def pricing(model, duals, customers: list, start_depot: Customer, capacity: int, RCI_constrs: dict):
    # CREATE GRAPH
    g = DiGraph(directed=True, n_res=1, elementary=True)

    # CONNECT EACH CUSTOMER TO SOURCE/SINK
    for u in customers:
        # print(f"Demand: {u.demand}, Weight: {dist(start_depot, u)}")
        edge_weight = dist(start_depot, u) - duals[u.id]
        g.add_edge("Source", str(u.id), res_cost=array([
                   float(u.demand)]), weight=edge_weight)
        # print(
        #     f"Demand: {0}, Weight: {dist(start_depot, u) - dual(model, u)} dist: {dist(start_depot, u)} dual: {dual(model, u)}")
        edge_weight = dist(start_depot, u) - RCI_term(model, u, start_depot, RCI_constrs)
        g.add_edge(str(u.id), "Sink", res_cost=array(
            [0.0]), weight=edge_weight)

    # CONNECT CUSTOMERS TO EACH OTHER
    for u in customers:
        for v in customers:
            if u != v:
                edge_weight = dist(u, v) - duals[v.id] - RCI_term(model, u, v, RCI_constrs)
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


def dual_dict(model, constraints: dict, customers: list):
    duals = {}
    for u in customers:
        duals[u.id] = model.getDual(constraints[u.id])

    return duals

def RCI_term(model, a: Customer, b: Customer, RCI_constrs: dict):
    if RCI_constrs == None:
        return 0
    applicable_constraints = RCI_constrs[a.id] - RCI_constrs[b.id]
    RCI_dual_val = 0
    for constr in applicable_constraints:
        RCI_dual_val += model.getDual(constr[0])
    # for constr_name in RCI_constrs:
    #     if a in RCI_constrs[constr_name] and b not in RCI_constrs[constr_name]:
    #         RCI_dual_val += model.getDual(constr_name)[0]

    return RCI_dual_val