import math
from data.read_problem_data import generate_problem
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, find_P
from utilities.compute_beta import compute_beta
from compute_all_inter_pair import compute_all_inter_pair


# PICK THE DATA SET TO WORK WITH
data_set = "A-n32-k5.vrp"

# SET DIVISOR FOR CAPACITY AND NUMBER OF LA NEIGHBORS
MY_DIVISOR = 20
NUM_LA_NEIGHBORS = 8


# READ IN PROBLEM DATA
customers, start_depot, end_depot, capacity = generate_problem(
    data_set, MY_DIVISOR, NUM_LA_NEIGHBORS)

# HERE ARE ALL OF THE DICTIONARIES YOU ASKED FOR
all_customers = []
LA_neighbors = {}  # values are a sorted list of closest NUM_LA_NEIGHBORS customers
dist_to_depot = {}
dist_mat = {}
demand = {}

# THIS WILL BUILD ALL OF THESE DICTIONARIES
for c in customers:
    all_customers.append(c.id)
    LA_neighbors[c.id] = [neighbor.id for neighbor in c.LA_neighbors]
    dist_to_depot[c.id] = math.hypot(c.x - start_depot.x, c.y - start_depot.y)
    demand[c.id] = c.demand
    for c2 in customers:
        dist_mat[c.id, c2.id] = math.hypot(c.x - c2.x, c.y - c2.y)


[dict_LA_2_ordering, dict_LA_2_cost] = compute_all_inter_pair(
    LA_neighbors, dist_mat, dist_to_depot, NUM_LA_NEIGHBORS, all_customers, capacity, demand)

# GO CRAZY HERE
# for c in all_customers[0:5]:
#     print(f"{c}'s LA_neighbors: {LA_neighbors[c]}")
#     print(f"{c}'s dist_to_depot: {dist_to_depot[c]}")
#     print(f"{c}'s demand: {demand[c]}")
#     for c2 in all_customers[0:5]:
#         print(f"Distance from {c} to {c2}: {dist_mat[c, c2]}")
#     print("\n")

# find_LA_arcs(customers, end_depot, capacity)
