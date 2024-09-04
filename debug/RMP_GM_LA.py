import math


def show_LA_arcs_in_solution(x_p: dict, model):
    for l in x_p:
        for arc_id in x_p[l]:
            var = x_p[l][arc_id]
            solution = model.getSolution(var)
            if solution > 0:
                print(
                    f"Arc variable {var.name} has value {round(solution, 2)}")


def show_graph_edges_in_solution(x_ij: dict, model):
    for l in x_ij:
        for (i_name, j_name) in x_ij[l]:
            var = x_ij[l][i_name, j_name]
            solution = model.getSolution(var)
            if solution > 0:
                print(
                    f"Graph variable {var.name} has value {round(solution, 2)}")


def compute_cost_from_LA_arcs_selected(x_p: dict, model, omega_y_l):
    total_arcs_cost = 0
    arc_costs_added = 0

    for l in x_p:
        for arc_id in x_p[l]:
            var = x_p[l][arc_id]
            solution = model.getSolution(var)
            if solution > 0:
                arc_found = False
                for y in omega_y_l[l]:
                    for arc in omega_y_l[l][y]:
                        if arc.id == arc_id:
                            print(
                                f"Arc {arc_id} with cost {round(arc.cost, 2)} selected {round(solution, 2)} times in the solution.")
                            total_arcs_cost += solution * arc.cost
                            arc_costs_added += 1
                            arc_found = True
                            break
                    if arc_found:
                        break

    print(f"Cost of all arcs: {round(total_arcs_cost, 2)}")
    print(f"Summed the cost of {arc_costs_added} different arcs")


def compute_cost_from_routes_departing_depot(x_ij: dict, model, customers, start_depot):
    total_departing_cost = 0
    cost = depot_dist(customers, start_depot)

    for l in x_ij:
        for (i_name, j_name) in x_ij[l]:
            if i_name.split('_')[0] == start_depot.id:
                var = x_ij[l][i_name, j_name]
                solution = model.getSolution(var)
                dest_id = j_name.split('_')[0]
                total_departing_cost += solution * cost[dest_id]

    print(f"Cost of all departing vehicles: {round(total_departing_cost, 2)}")


def depot_dist(customers, start_depot):
    cost = {}
    for u in customers:
        cost[u.id] = math.hypot(u.x - start_depot.x, u.y - start_depot.y)

    return cost


def check_coverage_over_arcs(x_p: dict, model, customers: list):
    epsilon = 0.0001
    coverage_dict = {}
    for u in customers:
        coverage_dict[u.id] = 0

    for l in x_p:
        for arc_id in x_p[l]:
            var = x_p[l][arc_id]
            solution = model.getSolution(var)
            if solution > 0:
                covered = var.name.split("_")
                for u_id in covered[2:]:
                    if u_id == "end":
                        continue
                    else:
                        coverage_dict[u_id] += solution

    not_covered_count = 0

    for u_id in coverage_dict:
        if coverage_dict[u_id] < (1 - epsilon):
            print(
                f"Customer {u_id} visited {coverage_dict[u_id]} times in solution over x_p")
            not_covered_count += 1

    if not_covered_count == 0:
        print("All customers covered at least once in solution over x_p")
    else:
        print(f"{not_covered_count} customers not covered")


def check_reduced_cost_of_gen_col(new_route, model, cover_constrs):
    route_cost = 0
    dual_sum = 0

    for (idx, u) in enumerate(new_route.visits[:-1]):
        v = new_route.visits[idx + 1]
        route_cost += math.hypot(u.x - v.x, u.y - v.y)

    for u in new_route.visits[1:-1]:
        dual_sum += model.getDual(cover_constrs[u.id])

    print(f"Route {[c.id for c in new_route.visits]} reduced cost: route.cost = {new_route.cost}, route_cost = {route_cost}, dual_sum = {dual_sum}, rc = {route_cost - dual_sum}")
