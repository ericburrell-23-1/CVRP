import numpy as np
import math
from models.data_structures.customer import Customer
from utilities.LA_neighbors import add_closest_neighbors


def generate_problem(data_set: str, MY_DIVISOR: int, NUM_LA_NEIGHBORS: int, CUSTOMER_SIZE_LIMIT=9999):
    """
    Loads problem data for specified `data_set` and returns a list of customers, start and end depots (as customer objects), and vehicle capacity for the problem.
    Has optional `CUSTOMER_SIZE_LIMIT` argument to truncate the set of customers.
    """
    print(f"Getting problem data for {data_set}")

    file_path = f"./data_sets/Uchoa/{data_set}"
    with open(file_path, "r") as file:
        lines = file.readlines()

    coord_section = False
    demand_section = False
    coordinates = {}
    demands = {}
    capacity = None
    start_depot = None
    end_depot = None

    for line in lines:
        if line.startswith("CAPACITY"):
            capacity = int(line.split(":")[1].strip())
        elif line.startswith("NODE_COORD_SECTION"):
            coord_section = True
            demand_section = False
            continue
        elif line.startswith("DEMAND_SECTION"):
            demand_section = True
            coord_section = False
            continue
        elif line.startswith("DEPOT_SECTION"):
            break

        if coord_section:
            columns = line.split()
            if len(columns) == 3:
                customer_id = int(columns[0])
                x = float(columns[1])
                y = float(columns[2])
                coordinates[customer_id] = (x, y)
            else:
                print("Error parsing coordinates")

        elif demand_section:
            columns = line.split()
            if len(columns) == 2:
                customer_id = int(columns[0])
                demand = int(columns[1])
                demands[customer_id] = demand
            else:
                print("Error parsing demand")

    customers = []
    for customer_id in coordinates:
        if customer_id in demands:
            x, y = coordinates[customer_id]
            demand = demands[customer_id]
            if customer_id == 1:
                if demands[customer_id] == 0:
                    start_depot = Customer(-1, x, y, 0) # CHANGED "start" to -1
                    end_depot = Customer(-2, x, y, 0) # CHANGED "end" to -2
                else:
                    print("Error: depot has nonzero demand")
            else:
                customers.append(Customer(int(customer_id - 1), # CHANGED FROM str TO int
                                 x, y, np.ceil(demand / MY_DIVISOR)))
        else:
            print(f"No demand found for customer {customer_id}")

    if len(customers) > CUSTOMER_SIZE_LIMIT:
        if CUSTOMER_SIZE_LIMIT < 1:
            print("WARNING: Enter positive customer size limit")
        else:
            customers = customers[:CUSTOMER_SIZE_LIMIT]

    add_closest_neighbors(customers, start_depot, NUM_LA_NEIGHBORS)
    capacity = int(np.ceil(capacity / MY_DIVISOR))

    return customers, start_depot, end_depot, capacity


def get_primitive_data(customers, start_depot):
    """
    Builds and returns `demands`, `costs` primitive dictionaries, as well as `N` and `N_plus` arrays. Uses -1 and -2 to denote the depot.
    """
    N_plus = []
    demands = {}
    costs = {}

    for u in customers:
        N_plus.append(u.id)
        demands[u.id] = u.demand

        # ADD INTER CUSTOMER COSTS
        for v in customers:
            if v.id == u.id:
                continue
            costs[(u.id, v.id)] = math.hypot(u.x - v.x, u.y - v.y)
        
        # ADD DEPOT COST
        depot_dist = math.hypot(u.x - start_depot.x, u.y - start_depot.y)
        for v_id in [-1, -2]:
            costs[(u.id, v_id)] = depot_dist
            costs[(v_id, u.id)] = depot_dist

    N_plus.extend([-1, -2])
    demands[-1] = 0
    demands[-2] = 0
    N = N_plus[:-2]

    return N, N_plus, demands, costs

