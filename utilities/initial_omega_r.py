from models.data_structures.route import Route

def initialize_omega_r(start_depot, customers, end_depot):
    omega_r = []
    for u in customers:
        visits = [start_depot, u, end_depot]
        omega_r.append(Route(visits, customers, start_depot, end_depot))

    return omega_r