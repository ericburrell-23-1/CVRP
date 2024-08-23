import math
from data.read_problem_data import generate_problem
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l, find_P
from new_LA_arcs import find_LA_arcs
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

find_LA_arcs(customers, end_depot, capacity)
# c23 = customers[22]
# c23_neighbors = [c.id for c in customers[22].LA_neighbors]
# print(f"{c23.id} has neighbors:{c23_neighbors}")
