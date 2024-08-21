import math
import itertools
import networkx as nx
from gurobipy import Model, GRB, quicksum
from models.data_structures.customer import Customer


def add_closest_neighbors(customers: list, start_depot: Customer, LAN_COUNT: int):
    for u in customers:
        customer_by_distance = []
        for v in customers + [start_depot]:
            if u != v:
                customer_by_distance.append((v, dist(u, v)))

        customer_by_distance.sort(key=lambda c: c[1])
        u.closest_neighbors = [neighbor[0]
                               for neighbor in customer_by_distance]

        add_LA_neighbors(u, LAN_COUNT)


def add_LA_neighbors(u: Customer, LA_NEIGHBOR_COUNT: int):

    if len(u.closest_neighbors) > LA_NEIGHBOR_COUNT:
        u.LA_neighbors = u.closest_neighbors[:LA_NEIGHBOR_COUNT]

        if any(neighbor.id == "start" for neighbor in u.LA_neighbors):
            u.LA_neighbors = [
                neighbor for neighbor in u.LA_neighbors if neighbor.id != "start"]
            u.LA_neighbors.append(u.closest_neighbors[LA_NEIGHBOR_COUNT])
    else:
        u.LA_neighbors = u.closest_neighbors
        if any(neighbor.id == "start" for neighbor in u.LA_neighbors):
            u.LA_neighbors = [
                neighbor for neighbor in u.LA_neighbors if neighbor.id != "start"]


def find_LA_arcs(customers: list, end_depot: Customer, capacity: int):
    omega_y = {}

    customer_dict = {}
    for u in customers:
        customer_dict[u.id] = u
    customer_dict["end"] = end_depot

    for u in customers:
        print(f"Finding LA-arcs for u = {u.id}")
        eligible_v = list(
            (set(customers) | {end_depot}) - {u} - set(u.LA_neighbors))
        for v in eligible_v:
            # print(f"\tFinding LA-arcs for v = {v.id}")
            for r in range(1, len(u.LA_neighbors) + 1):
                # print(f"\t\tFinding LA-arcs with {r} intermediate customers")
                for combination in itertools.combinations(u.LA_neighbors, r):
                    # COMPUTE THE LA ARC HERE
                    # if u.id == "5" and v.id == "17":
                    #     combo_list = list(combination)
                    #     print(
                    #         f"Combination: {[cust.id for cust in combo_list]}")
                    visit_list = list(combination) + [u]
                    total_demand = int(sum(
                        [cust.demand for cust in visit_list]))
                    if total_demand > (capacity - v.demand):
                        # if u.id == "5" and v.id == "17":
                        #     print(
                        #         f"Capacity exceeded: total_demand = {total_demand}")
                        continue
                    else:
                        LA_arc = most_efficient_path_by_MILP(
                            u, v, combination, customer_dict)
                        # print("\t\t\tFound an LA-arc")
                        y = (u.id, v.id, total_demand)
                        # if u.id == "5" and v.id == "17":
                        #     input(f"Adding LA-arc for y = {y} p = {LA_arc}")
                        if y in omega_y:
                            omega_y[y].append(LA_arc)
                        else:
                            omega_y[y] = [LA_arc]

    return omega_y


def most_efficient_path_by_MILP(u: Customer, v: Customer, N_p: tuple, customer_dict: dict):
    N_p_list = list(N_p)
    path = []
    tsp = Model("TSP")
    tsp.setParam('OutputFlag', 0)
    leaving_u = {}
    entering_v = {}
    between_custs = {}
    visit_order = {}

    u_dist_terms = []
    v_dist_terms = []
    between_dist_terms = []
    for cust in N_p_list:
        visit_order[cust.id] = tsp.addVar(
            vtype=GRB.INTEGER, lb=1, ub=len(N_p_list), name=f"visit_order_{cust.id}")
        leaving_u[cust.id] = tsp.addVar(
            vtype=GRB.BINARY, name=f"x_{u.id}_{cust.id}")
        u_dist_terms.append(dist(u, cust) * leaving_u[cust.id])
        entering_v[cust.id] = tsp.addVar(
            vtype=GRB.BINARY, name=f"x_{cust.id}_{v.id}")
        v_dist_terms.append(dist(v, cust) * entering_v[cust.id])

        for c2 in N_p_list:
            if c2 != cust:
                between_custs[cust.id, c2.id] = tsp.addVar(
                    vtype=GRB.BINARY, name=f"x_{cust.id}_{c2.id}")
                between_dist_terms.append(
                    dist(cust, c2) * between_custs[cust.id, c2.id])

    tsp.setObjective(quicksum(u_dist_terms + v_dist_terms +
                     between_dist_terms), GRB.MINIMIZE)

    tsp.addConstr(quicksum(leaving_u.values()) == 1, name="leaving_u")
    tsp.addConstr(quicksum(entering_v.values()) == 1, name="entering_v")

    for cust in N_p_list:
        tsp.addConstr(
            quicksum([leaving_u.get(cust.id, 0)] + [between_custs[c2.id, cust.id]
                     for c2 in N_p_list if c2 != cust]) == 1,
            name=f"flow_in_{cust.id}"
        )
        tsp.addConstr(
            quicksum([entering_v.get(cust.id, 0)] + [between_custs[cust.id, c2.id]
                     for c2 in N_p_list if c2 != cust]) == 1,
            name=f"flow_out_{cust.id}"
        )

        for c2 in N_p_list:
            if c2 != cust:
                tsp.addConstr(
                    (visit_order[cust.id] + 1) * between_custs[cust.id,
                                                               c2.id] == visit_order[c2.id] * between_custs[cust.id, c2.id]
                )

    tsp.optimize()

    if tsp.status == GRB.OPTIMAL:
        path = [customer_dict[u.id]]
        current = u.id
        for cust in N_p_list:
            if 0.99 < leaving_u.get(cust.id, 0).x < 1.01:
                path.append(customer_dict[cust.id])
                current = cust.id
                break
        while current != v.id:
            for c2 in N_p_list:
                var = between_custs.get((current, c2.id))
                if var is not None and 0.99 < var.x < 1.01:
                    path.append(c2.id)
                    current = c2.id
                    break
            if 0.99 < entering_v[current].x < 1.01:
                current = v.id
        path.append(customer_dict[v.id])
    else:
        path = []

    return path


def most_efficient_path_by_tsp_approx(u: Customer, v: Customer, N_p: tuple, customer_dict: dict):
    G = nx.DiGraph(directed=True)
    N_p_list = list(N_p)
    EXPENSIVE_EDGE_WEIGHT = 9999

    for cust in N_p_list:
        G.add_edge(u.id, cust.id, weight=dist(u, cust))
        G.add_edge(cust.id, u.id, weight=EXPENSIVE_EDGE_WEIGHT)
        G.add_edge(cust.id, v.id, weight=dist(cust, v))
        G.add_edge(v.id, cust.id, weight=EXPENSIVE_EDGE_WEIGHT)

    for cust in N_p_list:
        for c2 in N_p_list:
            if c2 != cust:
                G.add_edge(cust.id, c2.id, weight=dist(cust, c2))

    tsp_path = nx.approximation.traveling_salesman_problem(
        G, cycle=False, method=nx.approximation.greedy_tsp)
    if tsp_path[0] != u.id:
        tsp_path.reverse()

    LA_arc = [customer_dict[cust_id] for cust_id in tsp_path]

    return LA_arc


def dist(a: Customer, b: Customer):
    return math.hypot(a.x - b.x, a.y - b.y)
