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
