import xpress as xp
import networkx as nx
from networkx import DiGraph
from cspy import BiDirectional
from numpy import array
from bisect import bisect_left, insort
from typing import Callable
from algorithms.jy_opt.partial_pricing import RCI_term, epsilon, dual_dict, get_N2_from_complimentary_routes, add_demands

def positive_rc_pricing(beta: list, N: list, demands: dict, rmp: xp.problem, duals_cover: dict, capacity: int, cost: dict, RCI_constrs: dict=None):
    # PRE-COMPUTE REDUCED COSTS
    reduced_cost = {}
    etas = set()

    for u in N:
        reduced_cost[u, -2] = cost[-2, u] - duals_cover[u] - RCI_term(rmp, u, -2, RCI_constrs)
        etas.add((reduced_cost[u, -2] / demands[u]))


    for idx, u in enumerate(beta):
        for v in beta[idx + 1:]:
            reduced_cost[u, v] = cost[u, v] - duals_cover[u] - RCI_term(rmp, u, v, RCI_constrs)
            etas.add((reduced_cost[u, v] / demands[v]))
            
    eta = -1.0001 * min(etas)

    # CREATE GRAPH
    g = DiGraph(directed=True, n_res=1, elementary=False)

    # SOURCE CONNECTIONS
    for u in N:
        edge_weight = cost[-1, u]
        g.add_edge("Source", u, res_cost=array([0]), weight=edge_weight)

    # INTER-CUSTOMER CONNECTIONS
    for idx, u in enumerate(beta):
        for v in beta[idx + 1:]:
            edge_weight = reduced_cost[u, v] + (eta * demands[u])
            g.add_edge(u, v, res_cost=array([
                           float(demands[u])]), weight=edge_weight)
            
    # END DEPOT CONNECTIONS
    for u in N:
        edge_weight = reduced_cost[u, -2] + (eta * demands[u])
        g.add_edge(u, -2, res_cost=array([u]), weight=edge_weight)

    # PSEUDO-SINK AND SINK CONNECTIONS
    for d in range(0, capacity + 1):
        g.add_edge(-2, f"d{d}", res_cost=array([0]), weight=0)

        edge_weight = eta * (capacity - d)
        g.add_edge(f"d{d}", "Sink", res_cost=array([-float(d)]), weight=edge_weight)

    # DEFINE RESOURCE CONSTRAINTS
    max_res, min_res = array([0.0]), array([0.0]) # I think min/max should be 0, 0   float(capacity)

    total_offset = eta * capacity

    # SOLVE RCSPP TO GET PATH
    
    paths_found = []
    # solve_time = 0
    # update_time = 0
    while True:
        # op_start = time.time()
        bidirec = BiDirectional(g, max_res=max_res, min_res=min_res,
                                direction="both", elementary=False)
        bidirec.run()
        # solve_time += time.time() - op_start

        if bidirec.total_cost - total_offset > -epsilon:
            # print("Non-negative RC. Done iterating.")
            break

        # ADD NEW PATH AS COMPLIMENTARY COLUMN
        paths_found.append(bidirec.path[:-2]) # exclude pseudo-sink and sink

        # UPDATE EDGES USED IN PATH
        # op_start = time.time()
        for v in bidirec.path[1:-1]:
            node_beta_idx = beta.index(v)

            for u in ["Source"] + beta[:node_beta_idx]:
                g.edges[u, v]['weight'] += duals_cover[u]

        # update_time += time.time() - op_start

    return paths_found


def add_complimentary_column_edges(rmp: xp.problem, beta: list, N: list, demands: dict, capacity: int, cost: dict, constraints: dict, N2_pairs: set, cust_node_capacities: dict, RCI_constrs: dict=None):
    cover_duals = dual_dict(rmp, constraints, N)
    paths = relaxed_bellman_pricing(beta, N, demands, rmp, cover_duals, capacity, cost, RCI_constrs)

    if len(paths) != 0:
        N2_pairs.update(get_N2_from_complimentary_routes(paths))
        add_demands(paths, cust_node_capacities, capacity, demands)

        return True
    else:
        return False


def dijkstra_pricing(beta: list, N: list, demands: dict, rmp: xp.problem, duals_cover: dict, capacity: int, cost: dict, RCI_constrs: dict=None):
    reduced_cost = {}
    etas = set()

    for u in N:
        reduced_cost[u, -2] = cost[-2, u] - duals_cover[u] - RCI_term(rmp, u, -2, RCI_constrs)
        etas.add((reduced_cost[u, -2] / demands[u]))


    for idx, u in enumerate(beta):
        if u == -1:
            continue

        for v in beta[idx + 1:]:
            if v == -2:
                continue
            reduced_cost[u, v] = cost[u, v] - duals_cover[u] - RCI_term(rmp, u, v, RCI_constrs)
            etas.add((reduced_cost[u, v] / demands[u]))
            
    eta = (-1.0001) * min(etas)
    
    # CREATE GRAPH
    g = DiGraph(directed=True, n_res=1, elementary=False)

    # TRACK VISITED NODES
    visited = set()

    # DICT OF EDGES TO UPDATE EACH ITERATION
    u_edges = {}

    # SOURCE CONNECTIONS
    for u in N:
        u_edges[u] = []
        edge_weight = cost[-1, u]
        v_node = (u, capacity)
        g.add_edge("Source", v_node, weight=edge_weight)

    # RECURSIVE EDGE DRAWING FUNCTION
    def recursively_draw_edges(u_i, d_i):
        u_idx = beta.index(u_i)
        for u_j in beta[u_idx + 1:-1]:
            d_j = int(round(d_i - demands[u]))
            if d_j >= demands[u_j]:
                u_node = (u_i, d_i)
                v_node = (u_j, d_j)
                edge_weight = reduced_cost[u_i, u_j] + (eta * demands[u_i])
                g.add_edge(u_node, v_node, weight=edge_weight)
                u_edges[u_i].append((u_node, v_node))
                if v_node not in visited:
                    visited.add(v_node)
                    recursively_draw_edges(u_j, d_j)
        
        edge_weight = reduced_cost[u_i, -2] + (eta * d_i)
        g.add_edge((u_i, d_i), "Sink", weight=edge_weight)
        u_edges[u_i].append(((u_i, d_i), "Sink"))

    # BEGIN DRAWING EDGES FROM FIRST NODES AFTER SOURCE
    for u in beta[1:-1]:
        # print(f"Starting drawing edges at ({u}, capacity)")
        v_node = (u, capacity)
        visited.add(v_node)
        recursively_draw_edges(u, capacity)

    # SOLVE SPP
    total_offset = eta * capacity

    paths_found = []
    # print("Attempting to solve SPP to price over the graph.")
    while True:
        shortest_path = nx.dijkstra_path(g, "Source", "Sink", "weight")
        # rc = nx.path_weight(g, shortest_path, "weight") + total_offset
        path_weight = nx.path_weight(g, shortest_path, "weight")

        # print(f"Found a path with weight = {round(path_weight, 2)} and a total offset of {total_offset}")
        rc = path_weight - total_offset

        if rc > -epsilon:
            break
        else:
            cust_path = get_cust_path(shortest_path)
            paths_found.append(cust_path)
            update_edge_weights(cust_path, u_edges, total_offset, g)


    print(f"dijkstra_pricing found {len(paths_found)} new paths")
    return paths_found


def find_d_uvd(u_demands: list, target_demand):
    """Assumes `u_demands` is sorted, finds smallest value that is larger than `target_demand`"""
    idx = bisect_left(u_demands, target_demand)

    if idx < len(u_demands):
        return u_demands[idx]
    else:
        return 0

def relaxed_bellman_pricing(beta: list, N: list, demands: dict, rmp: xp.problem, duals_cover: dict, capacity: int, cost: dict, RCI_constrs: dict=None):
    reduced_cost = {}
    etas = set()

    for u in N:
        reduced_cost[u, -2] = cost[-2, u] - duals_cover[u] - RCI_term(rmp, u, -2, RCI_constrs)
        etas.add((reduced_cost[u, -2] / demands[u]))


    for idx, u in enumerate(beta):
        if u == -1:
            continue

        for v in beta[idx + 1:]:
            if v == -2:
                continue
            reduced_cost[u, v] = cost[u, v] - duals_cover[u] - RCI_term(rmp, u, v, RCI_constrs)
            etas.add((reduced_cost[u, v] / demands[u]))
            
    eta = 0 # (-1.0001) * min(etas)
    
    # CREATE GRAPH
    g = DiGraph(directed=True, n_res=1, elementary=False)

    # INITIALIZE CUSTOMER NODE DEMANDS
    demand_thresholds = {}
    for u in N:
        demand_thresholds[u] = [capacity]
    demand_thresholds[-2] = [0]

    # TRACK VISITED NODES
    visited = set()

    # DICT OF EDGES TO UPDATE EACH ITERATION
    u_edges = {}

    # SOURCE CONNECTIONS
    for u in N:
        u_edges[u] = []
        edge_weight = cost[-1, u]
        v_node = (u, capacity)
        g.add_edge("Source", v_node, weight=edge_weight)



    # RECURSIVE EDGE DRAWING FUNCTION
    def recursively_draw_edges(u_i, d_i):
        u_idx = beta.index(u_i)
        for u_j in beta[u_idx + 1:-1]:
            target_d_j = int(round(d_i - demands[u]))
            d_j = find_d_uvd(demand_thresholds[u_j], target_d_j)
            if d_j >= demands[u_j]:
                u_node = (u_i, d_i)
                v_node = (u_j, d_j)
                edge_weight = reduced_cost[u_i, u_j] + (eta * demands[u_i])
                g.add_edge(u_node, v_node, weight=edge_weight)
                u_edges[u_i].append((u_node, v_node))
                if v_node not in visited:
                    visited.add(v_node)
                    recursively_draw_edges(u_j, d_j)
        
        edge_weight = reduced_cost[u_i, -2] + (eta * d_i)
        g.add_edge((u_i, d_i), "Sink", weight=edge_weight)
        u_edges[u_i].append(((u_i, d_i), "Sink"))

    # BEGIN DRAWING EDGES FROM FIRST NODES AFTER SOURCE
    for u in beta[1:-1]:
        # print(f"Starting drawing edges at ({u}, capacity)")
        v_node = (u, capacity)
        visited.add(v_node)
        recursively_draw_edges(u, capacity)

    # SOLVE SPP
    total_offset = eta * capacity

    paths_found = []
    # print("Attempting to solve SPP to price over the graph.")
    while True:
        shortest_path = nx.bellman_ford_path(g, "Source", "Sink", "weight") # nx.dijkstra_path(g, "Source", "Sink", "weight")
        # rc = nx.path_weight(g, shortest_path, "weight") + total_offset
        path_weight = nx.path_weight(g, shortest_path, "weight")

        # print(f"Found a path with weight = {round(path_weight, 2)} and a total offset of {total_offset}")
        rc = path_weight # - total_offset

        if rc > -epsilon:
            print(f"Pricing done, rc = {round(rc, 2)}")
            break
        else:
            cust_path = get_cust_path(shortest_path)
            tot_demand = get_total_demand(cust_path, demands)
            if tot_demand <= capacity:
                print("Found a valid path")
                paths_found.append(cust_path)
                update_edge_weights(cust_path, u_edges, duals_cover, g)
            else:
                add_nodes_to_graph(g, shortest_path, demands, demand_thresholds, eta, recursively_draw_edges, visited, u_edges)


    print(f"dijkstra_pricing found {len(paths_found)} new paths")
    return paths_found



def add_nodes_to_graph(g: DiGraph, path: list, demands: dict, demand_thresholds: dict, eta: float, edge_drawing_func: Callable[[int, int], None], visited: set, u_edges: dict):
    print("Capacity violated, updating graph")
    for i in path[1:-2]:
        i_idx = path.index(i)
        j = path[i_idx + 1]

        (u_i, d_i) = i
        (u_j, d_j) = j

        d_j_hat = int(round(d_i - demands[u_i]))
        insort(demand_thresholds[u_j], d_j_hat)
        j_hat = (u_j, d_j_hat)

        for k in list(g.predecessors(j)):
            if k == "Source":
                continue

            (u_k, d_k) = k
            if d_k <= d_i:
                edge_weight = g[k][j]["weight"] + (eta * (d_j - d_j_hat))

                g.remove_edge(k, j)
                g.add_edge(k, j_hat, weight=edge_weight)

                u_edges[u_k].remove((k, j))
                u_edges[u_k].append((k, j_hat))

        visited.add(j_hat)
        edge_drawing_func(u_j, d_j_hat)





def get_total_demand(cust_path: list, demands: dict):
    tot_demand = 0

    for u in cust_path[1:-1]:
        tot_demand += demands[u]

    return tot_demand

def get_cust_path(path: list):
    cust_path = []
    for node in path:
        if node == "Source":
            cust_path.append(-1)
        elif node == "Sink":
            cust_path.append(-2)
        else:
            cust_path.append(node[0])

    return cust_path


def update_edge_weights(cust_path: list, u_edges: dict, cover_duals: dict, graph: DiGraph):
    # update_count = 0
    for u in cust_path[1:-1]:
        for i, j in u_edges[u]:
            graph.edges[i, j]["weight"] += cover_duals[u]
            # update_count += 1
        # print(f"Updated {update_count} edges starting at {u}")



def verify_positive_edge_weights(graph):
    for u, v, data in graph.edges(data=True):
        weight = data.get("weight", None)
        if weight is None:
            print(f"Edge ({u}, {v}) does not have a weight attribute.")
            return False
        elif weight <= 0:
            print(f"Edge ({u}, {v}) has a non-positive weight: {weight}")
            return False
    print("All edges have positive weights.")
    return True


