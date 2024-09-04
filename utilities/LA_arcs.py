import math
import time
import itertools
from models.data_structures.customer import Customer


class LA_arc_index:
    """
    Used to index all LA_Arcs and shortest paths while building LA-Arcs from P+. Consists of the tuple (u, v, N_hat), and is used to quickly check equality of these objects.
    """

    def __init__(self, u: Customer, v: Customer, N_hat: set):
        self.u = u
        self.v = v
        self.N_hat = N_hat
        self.name = self.build_name()

    def __eq__(self, other):
        if isinstance(other, LA_arc_index):
            return self.name == other.name
        else:
            return False

    def __hash__(self):
        return hash((self.u, self.v, tuple(sorted(self.N_hat, key=lambda c: c.id))))

    def __repr__(self):
        return f"LA_arc_index(u={self.u}, v={self.v}, N_hat={self.N_hat})"

    def build_name(self):
        obj_name = f"{self.u.id}"
        for w in sorted(self.N_hat, key=lambda c: c.id):
            obj_name += f"_{w.id}"

        obj_name += f"_{self.v.id}"

        return obj_name


class LA_Arc:
    def __init__(self, u: Customer, v: Customer, N_hat: list, cost: float):
        self.u = u
        self.v = v
        self.N_hat = N_hat
        self.cost = cost
        self.visits = [u] + N_hat + [v]
        self.demand = self.compute_demand()
        self.id = self.compute_id()

    def __eq__(self, other):
        if isinstance(other, LA_Arc):
            return self.id == other.id
        else:
            return False

    def __hash__(self):
        return hash((self.u, self.v, tuple(self.N_hat)))

    def __repr__(self):
        return f"LA_Arc(u={self.u}, v={self.v}, N_hat={self.N_hat}, cost={self.cost})"

    def compute_demand(self):
        demand = 0
        for cust in [self.u] + self.N_hat:
            demand += cust.demand

        return int(round(demand))

    def compute_id(self):
        arc_id = f"{self.u.id}"
        for cust in self.visits[1:]:
            arc_id += f"_{cust.id}"

        return arc_id


def powerset(s):
    x = len(s)

    masks = [1 << i for i in range(x)]
    for i in range(1 << x):
        yield [ss for mask, ss in zip(masks, s) if i & mask]


def find_P(customers: list, end_depot: Customer):
    start = time.time()
    P = set()
    count = 0
    for u in customers:
        # all_subsets = list(powerset(u.LA_neighbors))
        not_neighbors_u = (set(customers) | {
                           end_depot}) - (set(u.LA_neighbors) | {u})
        for v in not_neighbors_u:
            for N_hat in powerset(u.LA_neighbors):
                P.add(LA_arc_index(u, v, set(N_hat)))
                count += 1

    end = time.time()
    print(f"Calculated P in {round(end - start, 2)} seconds")
    return P


def find_P_plus(customers: list, end_depot: Customer):
    '''
    Returns a dictionary of all tuples of the form (u, v, N_hat), keyed by length of N_hat.
    '''
    start = time.time()
    print("Finding P")
    P = find_P(customers, end_depot)
    print(f"Found P ({len(P)} terms). Finding P+ from P")
    P_plus = {}
    names_in_P_plus = set()
    for k in range(0, len(customers[0].LA_neighbors) + 1):
        P_plus[k] = set()

    # repeat = 0
    # no_repeat = 0
    for p in P:
        if p.name not in names_in_P_plus:
            P_plus[len(p.N_hat)].add(p)
            names_in_P_plus.add(p.name)
            # no_repeat += 1
        # else:
        #     repeat += 1
        for w in p.N_hat:
            # for w in p.N_hat:
            N_hat = p.N_hat - {w}
            # if not (N_hat & set(w.LA_neighbors)) or p.v in w.LA_neighbors:
            new_arc_index = LA_arc_index(w, p.v, N_hat)
            if new_arc_index.name not in names_in_P_plus:
                P_plus[len(N_hat)].add(new_arc_index)
                names_in_P_plus.add(new_arc_index.name)
                #     no_repeat += 1
                # else:
                #     repeat += 1
                # input(f"Term {new_arc_index.name} was repeated")

    # print(
    #     f"If statement triggered {no_repeat} times, prevented {repeat} duplicates")

    # print(
    #     f"{customers[16].id}'s LA neighbors: {[c.id for c in customers[16].LA_neighbors]}")
    # for k in range(0, len(customers[0].LA_neighbors) + 1):
    #     # u_dict = {}
    #     count = 0
    #     for arc_index in P_plus[k]:
    #         # if k == 0:
    #         #     if arc_index.u.id not in u_dict:
    #         #         u_dict[arc_index.u.id] = 1
    #         #     else:
    #         #         u_dict[arc_index.u.id] += 1
    #         if arc_index not in P:
    #             count += 1
    #             # if k == 0:
    #             #     print(f"Arc in P+ but not P: {arc_index.name}")
    #     print(
    #         f"P_plus - P for |N| = {k} added {count} terms")
    #     # if k == 0:
    #     #     for u_id in u_dict:
    #     #         print(f"{u_dict[u_id]} arcs starting at {u_id} for k = {k}")

    end = time.time()
    print(f"Calculated P+ in {round(end - start, 2)} seconds")
    return P_plus


def find_LA_arcs(customers: list, end_depot: Customer, capacity: int):
    start = time.time()
    P_plus = find_P_plus(customers, end_depot)
    print(f"P+ identified.")

    omega_y = {}
    optimal_ordering = {}

    # for index in P_plus:
    #     size = len(P_plus[index])
    #     print(f"P_plus for |N| = {index} has {size} terms")

    # print("Getting base cases |N_hat| = 0")
    for p in P_plus[0]:
        new_arc = LA_Arc(p.u, p.v, [], dist(p.u, p.v))
        optimal_ordering[p] = new_arc
        if p.v not in p.u.LA_neighbors:
            y = (new_arc.u.id, new_arc.v.id, new_arc.demand)
            if y in omega_y:
                omega_y[y].append(new_arc)
            else:
                omega_y[y] = [new_arc]

    finding_lowest_cost_arc_time = 0
    start_cost = 0
    end_cost = 0
    for n_len in range(1, len(customers[0].LA_neighbors) + 1):
        # print(f"Getting LA_arcs with {n_len} intermediate customers")
        for p in P_plus[n_len]:
            min_cost = 9999999
            intermediate_cust_path = []
            start_cost = time.time()
            # input(f"Looking at P+ element: {p.name}")
            for w in p.N_hat:
                prev_p = LA_arc_index(w, p.v, (p.N_hat - {w}))
                # if prev_p not in optimal_ordering:
                #     input(f"Arc index for {prev_p.name} not found")
                #     continue
                predecessor = optimal_ordering[prev_p]
                cost = dist(p.u, w) + predecessor.cost
                # input(
                #     f"Exploring w = {w.id}, prev_p = {prev_p.name}, predecessor = {[c.id for c in predecessor.visits]}, predecessor cost = {predecessor.cost}, new cost = {cost}")

                if cost < min_cost:
                    min_cost = cost
                    intermediate_cust_path = [w] + \
                        optimal_ordering[prev_p].N_hat
            end_cost = time.time()
            finding_lowest_cost_arc_time += (end_cost - start_cost)

            new_arc = LA_Arc(p.u, p.v, intermediate_cust_path, min_cost)
            optimal_ordering[p] = new_arc
            if p.v not in p.u.LA_neighbors and new_arc.demand <= int(round(capacity - p.v.demand)):
                y = (new_arc.u.id, new_arc.v.id, new_arc.demand)
                if y in omega_y:
                    omega_y[y].append(new_arc)
                else:
                    omega_y[y] = [new_arc]

    # print(
    #     f"Omega_y has {len(omega_y)} different y values.")

    end = time.time()
    print(f"Found all LA Arcs in {round(end - start, 2)} seconds")
    print(
        f"Spent {round(finding_lowest_cost_arc_time, 2)} seconds computing costs")

    return omega_y


def compute_omega_y_l(beta: list, omega_y: dict):
    omega_y_l = {}

    for y in omega_y:
        for arc in omega_y[y]:
            consistent_arc = True
            for (idx, cust) in enumerate(arc.visits[:-1]):
                next_cust = arc.visits[idx + 1]
                if cust not in beta or next_cust not in beta:
                    print("Error: Customer in LA_arc not found in beta")
                    consistent_arc = False
                    break
                elif beta.index(cust) > beta.index(next_cust):
                    consistent_arc = False
                    break
                else:
                    continue

            if consistent_arc:
                if y in omega_y_l:
                    omega_y_l[y].append(arc)
                else:
                    omega_y_l[y] = [arc]

    return omega_y_l


def dist(a: Customer, b: Customer):
    return math.hypot(a.x - b.x, a.y - b.y)
