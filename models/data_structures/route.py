import math
from models.data_structures.customer import Customer


class Route:
    def __init__(self, visits: list, customers: list, start_depot: Customer, end_depot: Customer):
        self.visits = visits
        self.id = self.build_route_id()
        self.cost = self.compute_cost()
        self.demand = self.compute_demand()
        self.a_ul = self.compute_a_ul(customers)
        self.a_uvl = self.compute_a_uvl(customers, start_depot, end_depot)

    def build_route_id(self):
        id = "r"

        for stop in self.visits:
            id += f"_{stop.id}"

        return id

    def compute_cost(self):
        total_cost = 0
        if len(self.visits) < 2:
            return total_cost

        for i in range(1, len(self.visits)):
            leg_cost = math.hypot(
                self.visits[i].x - self.visits[i - 1].x, self.visits[i].y - self.visits[i - 1].y)
            total_cost += leg_cost

        return total_cost

    def compute_a_ul(self, customers):
        a = {}
        for u in customers:
            if u in self.visits:
                a[u.id] = 1
            else:
                a[u.id] = 0

        return a

    def compute_a_uvl(self, customers, start_depot, end_depot):
        a = {}
        for u in customers + [start_depot]:
            if u not in self.visits:
                u_index = -1
            else:
                u_index = self.visits.index(u)

            for v in set(customers + [end_depot]) - {u}:
                if u_index == -1:
                    a[u.id, v.id] = 0
                elif v not in self.visits:
                    a[u.id, v.id] = 0
                else:
                    v_index = self.visits.index(v)
                    if v_index == u_index + 1:
                        a[u.id, v.id] = 1
                    else:
                        a[u.id, v.id] = 0

        return a

    def compute_demand(self):
        total_demand = 0
        for u in self.visits:
            total_demand += u.demand

        return total_demand
