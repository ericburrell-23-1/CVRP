import numpy as np
from models.data_structures.customer import Customer
from utilities.LA_neighbors import add_closest_neighbors


def generate_problem(data_set: str, MY_DIVISOR: int, NUM_LA_NEIGHBORS: int, CUSTOMER_SIZE_LIMIT=9999):
    """
    Loads problem data for specified `data_set` and returns a list of customers, start and end depots (as customer objects), and vehicle capacity for the problem.
    Has optional `CUSTOMER_SIZE_LIMIT` argument to truncate the set of customers.
    """
    print(f"Getting problem data for {data_set}")

    file_path = f"./data_sets/XML/{data_set}"
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
                    start_depot = Customer("start", x, y, 0)
                    end_depot = Customer("end", x, y, 0)
                else:
                    print("Error: depot has nonzero demand")
            else:
                customers.append(Customer(str(customer_id - 1),
                                 x, y, np.ceil(demand / MY_DIVISOR)))
        else:
            print(f"No demand found for customer {customer_id}")

    if len(customers) > CUSTOMER_SIZE_LIMIT:
        if CUSTOMER_SIZE_LIMIT < 1:
            print("WARNING: Enter positive customer size limit")
        else:
            customers = customers[:CUSTOMER_SIZE_LIMIT]

    add_closest_neighbors(customers, start_depot, NUM_LA_NEIGHBORS)
    capacity = np.ceil(capacity / MY_DIVISOR)

    return customers, start_depot, end_depot, capacity
