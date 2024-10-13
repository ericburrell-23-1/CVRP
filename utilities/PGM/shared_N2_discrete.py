import xpress as xp
import scipy.sparse as sp
from numpy import ndarray
from utilities.compute_beta import node_sort, Node
from utilities.PGM.PGM import calculate_PGM_arc_weights, lowest_rc_route_in_family, epsilon



def consistent_N2_arcs(omega_y_l: list, N2_pairs: set, incumbent_arcs: list):
    """
    Given `omega_y_l` being the full list (items corresponding to each route family) of dictionaries (keyed by y) of LA-Arcs, returns a list containing the subsets of the original that are compliant with the pairs in the corresponding set in `N2_pairs`. Also returns the list of new arcs that were added this iteration, unless `incumbent_arcs` is an empty list.
    """
    consistent_arcs = []
    new_arcs = []
    for l, omega_y in enumerate(omega_y_l):
        consistent_arcs.append(dict())
        new_arcs.append(dict())
        for (u_p, v_p, d) in omega_y:
            if (u_p, v_p) in N2_pairs:
                consistent_arcs[l][(u_p, v_p, d)] = omega_y[(u_p, v_p, d)]
                if len(incumbent_arcs) <= l or (u_p, v_p, d) not in incumbent_arcs[l]:
                    new_arcs[l][(u_p, v_p, d)] = omega_y[(u_p, v_p, d)]

    if len(incumbent_arcs) == 0:
        return consistent_arcs
    
    return consistent_arcs, new_arcs
        



def consistent_N2_graphs(omega_R_plus: list, N2_pairs: set, incumbent_graphs: list):
    """
    Given the list of graphs `omega_R_plus` of the form (edges, nodes), returns the subsets of edges and nodes that are compliant with the corresponding set of pairs in `N2_pairs`. Also returns the list of new graph edges that were added this iteration, unless `incumbent_graphs` is an empty list.
    """
    consistent_graphs = []
    new_edges = []
    new_nodes = []
    nodes_added = 0
    max_l = len(incumbent_graphs)

    for l, (edges, nodes) in enumerate(omega_R_plus):
        consistent_edges = set()
        consistent_nodes = set()
        new_edges.append(set())
        new_nodes.append(set())
        for (i, j) in edges:
            if (i.u.id, j.u.id) in N2_pairs:
                consistent_nodes.add(i)
                consistent_nodes.add(j)
                consistent_edges.add((i, j))
                
                if len(incumbent_graphs) <= l or (i, j) not in incumbent_graphs[l][0]:
                    new_edges[l].add((i, j))

                if l < max_l and i not in incumbent_graphs[l][1]:
                    new_nodes[l].add(i)
                    nodes_added += 1

                if l < max_l and j not in incumbent_graphs[l][1]:
                    new_nodes[l].add(j)
                    nodes_added += 1

        sorted_nodes = sorted(consistent_nodes, key=node_sort)
        consistent_graphs.append((consistent_edges, sorted_nodes))

    if len(incumbent_graphs) == 0:
        return consistent_graphs
    
    print(f"Added {nodes_added} nodes to new_nodes.")
    
    return consistent_graphs, new_edges, new_nodes


def PGM(omega_r, omega_R_plus, y_arc_rows: dict, all_dual_constrs: list, uv_matrix: sp.csr_matrix, cost_vector: ndarray, arc_matrix: sp.csr_matrix, model: xp.problem, N2_pairs: set):
    rc_arc_vector = calculate_PGM_arc_weights(model, all_dual_constrs, uv_matrix, cost_vector, arc_matrix)
    continue_inner_optimization = False
    gm_calls = 0
    successful_gm_calls = 0
    new_N2 = set()

    for (l, _) in enumerate(omega_r):
                gm_calls += 1
                # start_solve = time.time()
                l_hat_l, rc = lowest_rc_route_in_family(omega_R_plus[l], y_arc_rows, rc_arc_vector)
                # end_solve = time.time()
                # print(f"Spent {round(end_solve - start_solve, 3)} seconds solving in lowest_rc_route function.")
                if rc < -epsilon:
                    successful_gm_calls += 1
                    continue_inner_optimization = True
                    if len(l_hat_l) > 1:
                        for idx, c1 in enumerate(l_hat_l[:-1]):
                            c2 = l_hat_l[idx + 1]
                            if (c1, c2) not in N2_pairs:
                                N2_pairs.add((c1, c2))
                                new_N2.add((c1, c2))

    return continue_inner_optimization, new_N2, gm_calls, successful_gm_calls




def draw_edges_from(node: Node, edges: set, visited: list, beta: list, N2_omega_y_l: dict):
            '''
            Draws edges from current node i = (u_i, d_i) to all new nodes j at (u_j, d_j), where beta.index(u_j) > beta.index(u_i), and d_j = d_i - d_y for some y = (u_i, u_j, d_y) in omega_y.
            '''
            beta_index = beta.index(node.u)
            for v in beta[beta_index + 1:]:
                if round(node.cap_remain - v.demand) >= node.u.demand:
                    for d in range(int(node.u.demand), int(round(node.cap_remain - v.demand + 1))):
                        y = (node.u.id, v.id, int(d))
                        if y in N2_omega_y_l:
                            new_node = Node(v, int(round(node.cap_remain - d)))
                            if (node, new_node) not in edges:
                                edges.add((node, new_node))
                                # print(f"Edge added ({node.name}, {new_node.name})")
                                if (v.id != "end") and (new_node not in visited):
                                    # print(f"Exploring new node {new_node.name}")
                                    visited.append(new_node)
                                    draw_edges_from(new_node)
                                elif v.id == "end" and (new_node not in visited):
                                    visited.append(new_node)



def augment_graphs(new_N2: set, omega_R_plus: list, N2_omega_y_l: list, new_arcs: list, betas: list, cust_by_id: dict):
    # ADD NODES/EDGES TO ALL GRAPHS
    for l, (edges, nodes) in enumerate(omega_R_plus):
        # LOOP OVER ALL EXISTING NODES
        for node in nodes:
            # LOOP OVER ALL NEW N2 EDGES AND CHECK IF NODE.U = N2.U
            for (u_id, v_id) in new_N2:
                if node.u.id == u_id:
                    # CHECK ARCS THAT CORRESPOND TO N2 AND HAVE VALID DEMAND
                    for (u_y_id, v_y_id, d_y) in new_arcs[l]:
                        if u_y_id == u_id and v_y_id == v_id and (node.cap_remain - d_y >= cust_by_id[v_id].demand):
                            # CREATE NEW NODE AND DRAW EDGES
                            new_node = Node(cust_by_id[v_id], int(round(node.cap_remain - d_y)))
                            if (node, new_node) not in edges:
                                edges.add((node, new_node))

                                if (v_id != "end") and (new_node not in nodes):
                                    nodes.append(new_node)
                                    draw_edges_from(new_node, edges, nodes, betas[l], N2_omega_y_l)

                                elif v_id == "end" and (new_node not in nodes):
                                    nodes.append(new_node)

        omega_R_plus[l] = (edges, sorted(nodes, key=node_sort))



