import math
from models.data_structures.customer import Customer


def show_closest_neighbors(customers: list, cust_index: int):
    neighbors = []
    customer = customers[cust_index]
    for u in customer.closest_neighbors:
        neighbors.append((u.id, dist(customer, u)))

    print(f"Customer {customer.id} neighbors (id, distance): {neighbors}")


def dist(a: Customer, b: Customer):
    return math.hypot(a.x - b.x, a.y - b.y)
