import math
import time
import itertools
from models.data_structures.customer import Customer


class LA_arc:
    def __init__(self, u: Customer, v: Customer, N_hat: list, cost: float):
        self.u = u
        self.v = v
        self.N_hat = N_hat
        self.cost = cost
        self.visits = [u] + N_hat + [v]
        self.demand = self.compute_demand()
        self.id = self.compute_id()

    def __eq__(self, other):
        if isinstance(other, LA_arc):
            return self.id == other.id
        else:
            return False

    def __hash__(self):
        return hash((self.u.id, self.v.id, tuple(self.N_hat)))

    def __repr__(self):
        return f"LA_arc_index(u={self.u}, v={self.v}, N_hat={self.N_hat})"

    def compute_demand(self):
        demand = 0
        for cust in [self.u] + self.N_hat:
            demand += cust.demand

        return int(demand)

    def compute_id(self):
        arc_id = f"{self.u.id}"
        for cust in self.visits[1:]:
            arc_id += f"_{cust.id}"

        return arc_id


def powerset(s):
    x = len(s)
    s_sorted = sorted(s)

    masks = [1 << i for i in range(x)]
    for i in range(1 << x):
        yield [ss for mask, ss in zip(masks, s_sorted) if i & mask]


def extract_customer_info(customers: list, depot: Customer):
    all_customers = []
    cust_dict = {}
    LA_neighbors = {}  # values are a sorted list of closest neighbors
    dist_matrix = {}
    demand = {}

    for c in customers + [depot]:
        all_customers.append(c.id)
        cust_dict[c.id] = c
        LA_neighbors[c.id] = [neighbor.id for neighbor in c.LA_neighbors]
        demand[c.id] = c.demand
        for c2 in customers + [depot]:
            dist_matrix[c.id, c2.id] = math.hypot(c.x - c2.x, c.y - c2.y)

    all_customers.remove(depot.id)

    return all_customers, cust_dict, LA_neighbors, dist_matrix, demand


def p_name(u, v, N_p):
    name_string = f"{u}"
    for w in N_p:
        name_string += f"_{w}"

    name_string += f"_{v}"

    return name_string


def find_P(customers: list, end_depot: Customer, LA_neighbors):
    P = {}

    for k in range(0, len(LA_neighbors[customers[0]]) + 1):
        P[k] = set()

    for u in customers:
        neighbor_subsets = list(powerset(LA_neighbors[u]))
        not_neighbors_u = (set(customers) | {
            end_depot.id}) - set(LA_neighbors[u]) - {u}
        for v in not_neighbors_u:
            for N_p in neighbor_subsets:
                P[len(N_p)].add((u, v, tuple(N_p)))

    count = 0
    for k in P:
        count += len(P[k])

    print(f"P has {count} terms")

    return P


def find_P_plus(customers: list, end_depot: Customer, LA_neighbors: dict):
    P = find_P(customers, end_depot, LA_neighbors)
    P_plus = {}
    names_in_P_plus = set()

    for k in range(0, len(LA_neighbors[customers[0]]) + 1):
        P_plus[k] = set()

    add_base_count = 0
    add_w_count = 0
    for k in P:
        for (u, v, N_p) in P[k]:
            new_p_name = p_name(u, v, N_p)
            names_in_P_plus.add(new_p_name)
            # add P element to P+
            P_plus[len(N_p)].add((u, v, N_p))
            add_base_count += 1
            # now loop through all N_p
            for w in N_p:
                new_N_p_set = set(N_p) - {w}
                if (v in LA_neighbors[w]):
                    # if (not (new_N_p_set & set(LA_neighbors[w]))) or (v in LA_neighbors[w]):
                    new_N_p = tuple(sorted(new_N_p_set))
                    new_p_name = p_name(w, v, new_N_p)
                    if new_p_name not in names_in_P_plus:
                        names_in_P_plus.add(new_p_name)
                        P_plus[len(new_N_p_set)].add((w, v, new_N_p))
                        add_w_count += 1

    print(
        f"Added {add_base_count} base terms and {add_w_count} additional terms to P+")
    count = 0
    for k in P_plus:
        count += len(P_plus[k])

    print(f"P+ has {count} terms")

    return P_plus


def find_LA_arcs(customers: list, end_depot: Customer, capacity: int):
    time_start = time.time()
    all_customers, cust_dict, LA_neighbors, dist, demand = extract_customer_info(
        customers, end_depot)

    P_plus = find_P_plus(all_customers, end_depot, LA_neighbors)

    optimal_ordering = {}  # all lowest cost arcs for a given p
    omega_y = {}  # a subset of optimal ordering that represents valid LA arcs

    for (u, v, N_p) in P_plus[0]:
        p_index = p_name(u, v, N_p)
        new_arc = LA_arc(cust_dict[u], cust_dict[v],
                         [], dist[u, v])
        # print(f"Adding arc for {p_index}")
        optimal_ordering[p_index] = new_arc
        if v not in LA_neighbors[u]:
            y = (u, v, new_arc.demand)
            omega_y[y] = [new_arc]

    # finding_lowest_cost_arc_time = 0
    # start_cost = 0
    # end_cost = 0

    for n_len in range(1, len(customers[0].LA_neighbors) + 1):
        print(f"Getting LA_arcs with {n_len} intermediate customers")
        for (u, v, N_p) in P_plus[n_len]:
            min_cost = 9999999
            intermediate_cust_path = []
            # start_cost = time.time()
            for w in N_p:
                prev_p_index = p_name(w, v, sorted(set(N_p) - {w}))
                # input(f"Checking for {prev_p_index} in optimal ordering dict")
                cost = dist[u, w] + optimal_ordering[prev_p_index].cost
                if cost < min_cost:
                    min_cost = cost
                    intermediate_cust_path = [cust_dict[w]] + \
                        optimal_ordering[prev_p_index].N_hat
            # end_cost = time.time()
            # finding_lowest_cost_arc_time += (end_cost - start_cost)

            p_index = p_name(u, v, N_p)

            new_arc = LA_arc(cust_dict[u], cust_dict[v],
                             intermediate_cust_path, min_cost)
            optimal_ordering[p_index] = new_arc
            if v not in LA_neighbors[u] and new_arc.demand <= capacity - demand[v]:
                y = (u, v, new_arc.demand)
                if y in omega_y:
                    omega_y[y].append(new_arc)
                else:
                    omega_y[y] = [new_arc]
    time_end = time.time()
    print(f"Found all LA arcs in {time_end - time_start} seconds")

    # print(
    #     f"Omega_y has {len(omega_y)} different y values.")

    # end = time.time()
    # print(f"Found all LA Arcs in {round(end - start, 2)} seconds")
    # print(
    #     f"Spent {round(finding_lowest_cost_arc_time, 2)} seconds computing costs")

    return omega_y
