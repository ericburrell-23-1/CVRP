import math


def check_route_not_in_graph(route, edges):
    for u in route.visits[:-1]:
        v = route.visits[route.visits.index(u) + 1]
        violation = True
        for (i, j) in edges:
            if i.u == u and j.u == v:
                violation = False
                break
        if violation == True:
            print(
                f"❌ Edge containing {u.id} -> {v.id} not in new graph")


def check_route_reduced_cost(model, constraints, customers, start_depot, end_depot, route):
    dist = {}
    for u in customers + [start_depot]:
        for v in customers + [end_depot]:
            dist[u.id, v.id] = math.hypot(u.x - v.x, u.y - v.y)

    cost_sum = 0
    for (idx, u) in enumerate(route.visits[:-1]):
        v = route.visits[idx + 1]
        cost_sum += dist[u.id, v.id]

    dual_sum = 0
    for u in route.visits[1:-1]:
        dual_sum += model.getDual(constraints[u.id])

    print(
        f"Manual check of rc -> route cost = {cost_sum}, duals = {dual_sum}, rc = {cost_sum - dual_sum}")
