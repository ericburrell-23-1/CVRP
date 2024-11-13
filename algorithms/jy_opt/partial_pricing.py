import time
import xpress as xp
from cspy import BiDirectional
from networkx import DiGraph
from numpy import array
from bisect import insort
from models.data_structures.customer import Customer
epsilon = 0.00001

def add_complimentary_column_edges(rmp: xp.problem, beta: list, constraints: dict, N: list, demands: dict, capacity: int, N2_pairs: set, costs: dict, cust_node_capacities: dict):
    """Adds edges to N2 and capacities for each u using similar process to partial pricing, from existing beta, without adding new graphs"""
    print("Doing partial pricing:")
    op_start = time.time()
    duals = dual_dict(rmp, constraints, N)
    print(f"Building dict of dual values took {round(time.time() - op_start, 3)} sec.")

    generated_routes = []
    RCI_constrs = constraints["RCI"]

    op_start = time.time()
    paths_found = pricing_from_beta(beta[1:-1], N, demands, rmp, duals, capacity, costs, RCI_constrs)
    print(f"Finding paths took a total of {round(time.time() - op_start, 3)} sec.")

    # print("Paths found. Building routes...")
    op_start = time.time()
    for path in paths_found:
        visits = []
        for id in path:
            if id == "Source":
                visits.append(-1)
            elif id == "Sink":
                visits.append(-2)
            else:
                visits.append(int(id))

        generated_routes.append(visits)

    print(f"Building routes took {round(time.time() - op_start, 3)} sec.")

    if len(generated_routes) != 0:
        op_start = time.time()
        N2_pairs.update(get_N2_from_complimentary_routes(generated_routes))
        add_demands(generated_routes, cust_node_capacities, capacity, demands)
        print(f"Updating N2 and demands took {round(time.time() - op_start, 3)} sec.")

        return True
    else:
        return False




def get_N2_from_complimentary_routes(generated_routes: list):
    """Adds any customer pair (u,v) to N2 if u appears before v in any of the generated routes."""
    new_N2 = set()

    for l in generated_routes:
        for idx, u in enumerate(l[:-2]):
            if u == -1:
                continue
            for v in l[idx + 1:-1]:
                new_N2.add((u, v))

    return new_N2

def add_demands(generated_routes: list, cust_node_capacities: dict, capacity: int, demands: dict):
    for l in generated_routes:
        cap_remain = capacity
        for idx, u in enumerate(l[:-2]):
            if u == -1:
                continue
            cap_remain -= demands[u]
            cap_remain = int(round(cap_remain))
            for v in l[idx + 1:-1]:
                if cap_remain not in cust_node_capacities[v]:
                    insort(cust_node_capacities[v], cap_remain)


# def partial_pricing_PGM(rmp: xp.problem, constraints: dict, customers: list, start_depot: Customer, end_depot: Customer, capacity: int, omega_r: list, omega_R_plus: list, omega_y_l: list, omega_y: dict, N2_pairs: list, RCI_constrs: dict = None, time_limit = 999999):
#     duals = dual_dict(rmp, constraints, customers)
#     # print("Computing beta")
#     unique_seed = len(omega_r) + 10
#     beta = compute_beta_from_nothing(customers, unique_seed)
#     # print("Finished computing beta")
#     # print(time_limit)

#     cust_by_id = {}
#     for u in customers:
#         cust_by_id[u.id] = u

#     generated_routes = []

#     pricing_tl = time_limit - (time.time() - start_time)
#         # print(f"Reduced cost = {reduced_cost}; going again")
#     paths_found = pricing_from_beta(beta, customers, start_depot, end_depot, rmp, duals, capacity, cust_by_id, RCI_constrs, pricing_tl)

#         # print("Path found. Building Route")
#     for path in paths_found:
#         visits = []
#         for id in path:
#             if id == "Source":
#                 visits.append(start_depot)
#             elif id == "Sink":
#                 visits.append(end_depot)
#             else:
#                 visits.append(cust_by_id[id])
#                 duals[id] = 0

#         generated_routes.append(visits)


#     if len(generated_routes) > 0:
#         beta.insert(0, start_depot)
#         beta.append(end_depot)
#         omega_r.append(Route(generated_routes[0], customers, start_depot, end_depot))
#         omega_y_l.append(compute_omega_y_l(beta, omega_y))
#         N2_pairs.append(get_N2_from_complimentary_routes(generated_routes))
#         return True, beta

#     return False, []


def pricing_from_beta(beta, N, demands, rmp, duals, capacity, cost, RCI_constrs=None):
    op_start = time.time()
    # CREATE GRAPH
    g = DiGraph(directed=True, n_res=1, elementary=False)

    # SOURCE/SINK CONNECTIONS
    for u in N:
        edge_weight = cost[-1, u] - duals[u]
        g.add_edge("Source", u, res_cost=array([
                   float(demands[u])]), weight=edge_weight)
        edge_weight = cost[-2, u] - RCI_term(rmp, u, -2, RCI_constrs)
        g.add_edge(u, "Sink", res_cost=array(
            [0.0]), weight=edge_weight)
        
    # INTER-CUSTOMER CONNECTIONS
    for idx, u in enumerate(beta):
        for v in beta[idx + 1:]:
            edge_weight = cost[u, v] - duals[v] - RCI_term(rmp, u, v, RCI_constrs)
            g.add_edge(u, v, res_cost=array([
                           float(demands[v])]), weight=edge_weight)
            
    # DEFINE RESOURCE CONSTRAINTS
    max_res, min_res = array([capacity + 1]), array([0.0])

    print(f"Building pricing graph took {round(time.time() - op_start, 3)} sec.")

    # SOLVE RCSPP TO GET PATH
    
    paths_found = []
    solve_time = 0
    update_time = 0
    while True:
        op_start = time.time()
        bidirec = BiDirectional(g, max_res=max_res, min_res=min_res,
                                direction="both", elementary=False)
        # print("Solving for path...")
        bidirec.run()
        solve_time += time.time() - op_start
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
        op_start = time.time()
        for v in bidirec.path[1:-1]:
            node_beta_idx = beta.index(v)

            for u in ["Source"] + beta[:node_beta_idx]:
                g.edges[u, v]['weight'] += duals[v]

        update_time += time.time() - op_start

    print(f"Found {len(paths_found)} complimentary paths.")
    print(f"Solving the RCSPP took {round(solve_time, 3)} sec.")
    print(f"Updating graph edges took {round(update_time, 3)} sec.")
            

    # end_solve = time.time()
    # print(f"Solved RCSPP in {round(end_solve - start_solve, 2)} seconds")
    # print(f"New path = {bidirec.path}")

    print(f"regular pricing found {len(paths_found)} new paths")
    return paths_found


def dual_dict(rmp, constraints: dict, N: list):
    duals = {}
    for u in N:
        duals[u] = rmp.getDual(constraints[tuple(['Cover',u])])

    return duals

def RCI_term(rmp, u, v, RCI_constrs: dict):
    if RCI_constrs == None:
        return 0
    
    RCIs = RCI_constrs.get((u, v), [])
    RCI_val = 0
    for constr in RCIs:
        RCI_val += rmp.getDual(constr)

    return RCI_val

    
    
    
