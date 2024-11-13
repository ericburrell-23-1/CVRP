from utilities.compute_beta import rand_order

def compute_beta(route: list, customers: list):
    """
    Accepts a list of customer objects `route` and all `customers`, and returns beta as a list of ids, starting with -1 and ending with -2.
    `route` should include start and end depots.
    """
    beta = []
    for c in route:
        beta.append(c.id)

    customers_to_add = rand_order(set(customers) - set(route), 39)

    for v in customers_to_add:
        for u in v.closest_neighbors:
            if u.id in beta:
                beta.insert(beta.index(u.id) + 1, v.id)
                break

    beta[0] = -1
    beta[-1] = -2
    # print(f"Beta = {[u.id for u in beta]}")
    return beta