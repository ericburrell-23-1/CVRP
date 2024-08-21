from gurobipy import GRB, Model


def count_constrs(model: Model, customers: list, omega_r_plus: list):
    constrs = model.getConstrs()
    cover_constrs = [c for c in constrs if c.constrName.startswith("cover_")]
    flow_constrs = [c for c in constrs if c.constrName.startswith("flow_")]

    if len(cover_constrs) == len(customers):
        print(f"✅ Found {len(cover_constrs)} coverage constraints.")

    for u in customers:
        if not any(c.constrName == f"cover_{u.id}" for c in cover_constrs):
            print(f"❌ Coverage constraint for {u.id} missing")

    total_nodes = 0
    for graph in omega_r_plus:
        total_nodes += len(graph[1])

    print(f"{len(flow_constrs)} flow constraints for {total_nodes} nodes")
    for (l, graph) in enumerate(omega_r_plus):
        nodes = graph[1]
        for i in nodes:
            if i.u.id != "start" and i.u.id != "end":
                if not any(c.constrName == f"flow_l{l}_{i.name}" for c in flow_constrs):
                    print(
                        f"❌ Flow constraint missing for l = {l} node = {i.name}")


def show_routes_traversed(model):
    routes = []
    routes_traversed = [
        var.varName for var in model.getVars() if var.x > 0.99 and var.x < 1.01]
    starting_edges = [
        edge for edge in routes_traversed if edge.startswith("x_start")]

    def find_next_edge(current_edge):
        # Get the end node of the current edge
        current_end = current_edge.split("_")[3]
        for edge in routes_traversed:
            start_node = edge.split("_")[1]  # Get the start node of this edge
            if current_end == start_node:  # If the end node matches the start node of the next edge
                # If the end node is the end depot
                if edge.split("_")[3] == "end":
                    return f" -> {edge.split('_')[1]},{edge.split('_')[2]} -> {edge.split('_')[3]},{edge.split('_')[4]}"
                else:
                    return f" -> {edge.split('_')[1]},{edge.split('_')[2]}" + find_next_edge(edge)
        return ""

    for start_edge in starting_edges:
        new_route = f"start,{start_edge.split('_')[2]}"
        new_route += find_next_edge(start_edge)
        routes.append(new_route)

    routes_traversed = sorted(routes_traversed, key=lambda e: e.split("_")[2])

    print(f"All Routes: {routes_traversed}")

    for route in routes:
        print(route)
