import math
import time
import xpress as xp
from cspy import BiDirectional
from networkx import DiGraph
from numpy import array
from utilities.generate_col import dual_dict, RCI_term, dist
from utilities.compute_beta import rand_order, create_LA_arc_graph
from utilities.LA_arcs import compute_omega_y_l
from models.data_structures.customer import Customer
from models.data_structures.route import Route

epsilon = 0.00001

# def partial_pricing(model: xp.problem, constraints: dict, customers: list, start_depot: Customer, end_depot: Customer, capacity: int, RCI_constrs: dict = None, time_limit = 999999):
#     start_time = time.time()
#     duals = dual_dict(model, constraints, customers)
#     # print("Computing beta")
#     beta = compute_beta_from_nothing(customers, 42)
#     # print("Finished computing beta")
#     # print(time_limit)

#     cust_by_id = {}
#     for u in customers:
#         cust_by_id[u.id] = u

#     generated_routes = []
#     continue_iter = True
#     reduced_cost = None
#     excess_pricing_time = 0

#     while continue_iter:
#         print(f"Reduced cost = {reduced_cost}; going again")
#         visits_by_id, reduced_cost = pricing_from_beta(beta, customers, start_depot, model, duals, capacity, RCI_constrs)

#         # print("Path found. Building Route")

#         visits = []
#         for id in visits_by_id:
#             if id == "Source":
#                 visits.append(start_depot)
#             elif id == "Sink":
#                 visits.append(end_depot)
#             else:
#                 visits.append(cust_by_id[id])
#                 duals[id] = 0

#         run_time = time.time() - start_time
#         if run_time > time_limit:
#             print("Partial pricing time limit reached")
#             excess_pricing_time = run_time - time_limit
#             break
#         elif reduced_cost < -0.00001:
#             generated_routes.append(Route(visits, customers, start_depot, end_depot))
#         else:
#             continue_iter = False


#     # print("Route created. Returning")

#     return generated_routes, excess_pricing_time






def compute_beta_from_nothing(customers, seed):
    customers_to_add = rand_order(customers, seed)
    beta = [customers_to_add[0]]
    for v in customers_to_add[1:]:
        for u in v.closest_neighbors:
            if u in beta:
                beta.insert(beta.index(u) + 1, v)
                break
    
    return beta



def pricing_from_beta(beta, customers, start_depot, end_depot, model, duals, capacity, cust_by_id, RCI_constrs=None):
    # CREATE GRAPH
    # print("Setting up pricing graph")
    # start_setup = time.time()
    # print("Building partial pricing graph...")
    g = DiGraph(directed=True, n_res=1, elementary=True)

    # CONNECT EACH CUSTOMER TO SOURCE/SINK
    # edge_count = 0
    for u in customers:
        # print(f"Demand: {u.demand}, Weight: {dist(start_depot, u)}")
        edge_weight = dist(start_depot, u) - duals[u.id]
        g.add_edge("Source", str(u.id), res_cost=array([
                   float(u.demand)]), weight=edge_weight)
        # edge_count += 1
        # print(
        #     f"Demand: {0}, Weight: {dist(start_depot, u) - dual(model, u)} dist: {dist(start_depot, u)} dual: {dual(model, u)}")
        edge_weight = dist(end_depot, u) - RCI_term(model, u, start_depot, RCI_constrs)
        g.add_edge(str(u.id), "Sink", res_cost=array(
            [0.0]), weight=edge_weight)
        
    # print("added all source/sink connections")
    
    # print("Added source/sink connections. Adding inter-customer connections...")
    for idx, u in enumerate(beta):
        for v in beta[idx + 1:]:
            edge_weight = dist(u, v) - duals[v.id] - RCI_term(model, u, v, RCI_constrs)
            g.add_edge(str(u.id), str(v.id), res_cost=array([
                           float(v.demand)]), weight=edge_weight)
            
    # print("Added all inter-customer edges. Solving now.")
    # DEFINE RESOURCE CONSTRAINTS
    max_res, min_res = array([capacity + 1]), array([0.0])

    # RUN LABELING ALG TO GET PATH
    

    # end_setup = time.time()
    # print(f"Finished setup in {round(end_setup - start_setup, 2)} seconds. Solving RCSPP")
    # start_solve = time.time()
    paths_found = []
    while True:
        bidirec = BiDirectional(g, max_res=max_res, min_res=min_res,
                                direction="both", elementary=False)
        # print("Solving for path...")
        bidirec.run()
        # print("Done solving.")

        # CHECK FOR NEGATIVE RC
        # if bidirec.total_cost == None:
        #     # print("Total Cost was None")
        #     break
        if bidirec.total_cost > -epsilon:
            # print("Non-negative RC. Done iterating.")
            break

        # run_time = time.time() - start_time
        # if run_time > time_limit:
        #     print("Partial pricing time limit reached")
        #     continue_iter = False
        #     break

        # ADD NEW PATH AS COMPLIMENTARY COLUMN
        paths_found.append(bidirec.path)

        # print("Resetting edge weights...")
        # UPDATE EDGES USED IN PATH
        for v_id in bidirec.path[1:-1]:
            v = cust_by_id[v_id]
            node_beta_idx = beta.index(v)

            for u_id in ["Source"] + [u.id for u in beta[:node_beta_idx]]:
                g.edges[u_id, v_id]['weight'] += duals[v_id]
            

    # end_solve = time.time()
    # print(f"Solved RCSPP in {round(end_solve - start_solve, 2)} seconds")
    # print(f"New path = {bidirec.path}")

    return paths_found



def partial_pricing_PGM(model: xp.problem, constraints: dict, customers: list, start_depot: Customer, end_depot: Customer, capacity: int, omega_r: list, omega_R_plus: list, omega_y_l: list, omega_y: dict, N2_pairs: list, RCI_constrs: dict = None, time_limit = 999999):
    # start_time = time.time()
    duals = dual_dict(model, constraints, customers)
    # print("Computing beta")
    unique_seed = len(omega_r) + 10
    beta = compute_beta_from_nothing(customers, unique_seed)
    # print("Finished computing beta")
    # print(time_limit)

    cust_by_id = {}
    for u in customers:
        cust_by_id[u.id] = u

    generated_routes = []

        # print(f"Reduced cost = {reduced_cost}; going again")
    paths_found = pricing_from_beta(beta, customers, start_depot, end_depot, model, duals, capacity, cust_by_id, RCI_constrs)

        # print("Path found. Building Route")
    for path in paths_found:
        visits = []
        for id in path:
            if id == "Source":
                visits.append(start_depot)
            elif id == "Sink":
                visits.append(end_depot)
            else:
                visits.append(cust_by_id[id])
                duals[id] = 0

        generated_routes.append(visits)


    if len(generated_routes) > 0:
        beta.insert(0, start_depot)
        beta.append(end_depot)
        omega_r.append(Route(generated_routes[0], customers, start_depot, end_depot))
        omega_y_l.append(compute_omega_y_l(beta, omega_y))
        N2_pairs.append(get_N2_from_complimentary_routes(generated_routes))
        return True, beta

    return False, []


def get_N2_from_complimentary_routes(generated_routes: list):
    """Adds any customer pair (u,v) to N2 if u appears before v in any of the generated routes."""
    new_N2 = set()

    for l in generated_routes:
        for idx, u in enumerate(l[:-2]):
            if u.id == "start":
                continue
            for v in l[idx + 1:]:
                new_N2.add((u.id, v.id))

    return new_N2


def add_complimentary_column_edges(model: xp.problem, beta: list, cover_constrs: dict, customers: list, start_depot: Customer, end_depot: Customer, capacity: int, omega_r: list, omega_R_plus: list, omega_y_l: list, omega_y: dict, N2_pairs: list):
    """Adds edges to N2 using similar process to partial pricing, from existing beta, without adding new graphs"""
    # print("Building dual dictionary...")
    duals = dual_dict(model, cover_constrs, customers)

    # print("Building customer dictionary...")
    cust_by_id = {}
    for u in customers:
        cust_by_id[u.id] = u

    generated_routes = []

    paths_found = pricing_from_beta(beta[1:-1], customers, start_depot, end_depot, model, duals, capacity, cust_by_id)

    # print("Paths found. Building routes...")
    for path in paths_found:
        visits = []
        for id in path:
            if id == "Source":
                visits.append(start_depot)
            elif id == "Sink":
                visits.append(end_depot)
            else:
                visits.append(cust_by_id[id])
                duals[id] = 0

        generated_routes.append(visits)


    N2_pairs[0].update(get_N2_from_complimentary_routes(generated_routes))

