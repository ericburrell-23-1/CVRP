import math
import time
from cspy import BiDirectional
from networkx import DiGraph
from numpy import array
from utilities.generate_col import dual_dict, RCI_term, dist
from utilities.compute_beta import rand_order
from models.data_structures.customer import Customer
from models.data_structures.route import Route

def partial_pricing(model, constraints: dict, customers: list, start_depot: Customer, end_depot: Customer, capacity: int, RCI_constrs: dict = None, time_limit = 999999):
    start_time = time.time()
    duals = dual_dict(model, constraints, customers)
    # print("Computing beta")
    beta = compute_beta_from_nothing(customers)
    # print("Finished computing beta")
    # print(time_limit)

    cust_by_id = {}
    for u in customers:
        cust_by_id[u.id] = u

    generated_routes = []
    continue_iter = True
    reduced_cost = None
    excess_pricing_time = 0

    while continue_iter:
        print(f"Reduced cost = {reduced_cost}; going again")
        visits_by_id, reduced_cost = pricing_from_beta(beta, customers, start_depot, model, duals, capacity, RCI_constrs)

        # print("Path found. Building Route")

        visits = []
        for id in visits_by_id:
            if id == "Source":
                visits.append(start_depot)
            elif id == "Sink":
                visits.append(end_depot)
            else:
                visits.append(cust_by_id[id])
                duals[id] = 0

        run_time = time.time() - start_time
        if run_time > time_limit:
            print("Partial pricing time limit reached")
            excess_pricing_time = run_time - time_limit
            break
        elif reduced_cost < -0.00001:
            generated_routes.append(Route(visits, customers, start_depot, end_depot))
        else:
            continue_iter = False


    # print("Route created. Returning")

    return generated_routes, excess_pricing_time






def compute_beta_from_nothing(customers):
    customers_to_add = rand_order(customers, 42)
    beta = [customers_to_add[0]]
    for v in customers_to_add[1:]:
        for u in v.closest_neighbors:
            if u in beta:
                beta.insert(beta.index(u) + 1, v)
                break
    
    return beta



def pricing_from_beta(beta, customers, start_depot, model, duals, capacity, RCI_constrs=None):
    # CREATE GRAPH
    print("Setting up pricing graph")
    start_setup = time.time()
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
        edge_weight = dist(start_depot, u) - RCI_term(model, u, start_depot, RCI_constrs)
        g.add_edge(str(u.id), "Sink", res_cost=array(
            [0.0]), weight=edge_weight)
        
    # print("added all source/sink connections")
    
    for idx, u in enumerate(beta):
        for v in beta[idx + 1:]:
            edge_weight = dist(u, v) - duals[v.id] - RCI_term(model, u, v, RCI_constrs)
            g.add_edge(str(u.id), str(v.id), res_cost=array([
                           float(v.demand)]), weight=edge_weight)
            
    # print("Added all inter-customer edges. Solving now.")
    # DEFINE RESOURCE CONSTRAINTS
    max_res, min_res = array([capacity + 1]), array([0.0])

    # RUN LABELING ALG TO GET PATH
    bidirec = BiDirectional(g, max_res=max_res, min_res=min_res,
                            direction="both", elementary=False)
    

    end_setup = time.time()
    print(f"Finished setup in {round(end_setup - start_setup, 2)} seconds. Solving RCSPP")
    start_solve = time.time()
    bidirec.run()
    end_solve = time.time()
    print(f"Solved RCSPP in {round(end_solve - start_solve, 2)} seconds")
    print(f"New path = {bidirec.path}")

    return bidirec.path, bidirec.total_cost