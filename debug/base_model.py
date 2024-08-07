import math


def compute_base_model_objective(customers, start_depot):
    total_dist = 0
    for customer in customers:
        leg_dist = math.hypot(customer.x - start_depot.x,
                              customer.y - start_depot.y)

        total_dist += (2 * leg_dist)

    print(f"Base model relaxation should return an objective of {total_dist}")
