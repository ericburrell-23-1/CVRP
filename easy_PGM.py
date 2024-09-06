import copy
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.compute_beta import compute_beta, create_LA_arc_graph, node_sort
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l
from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model
from debug.RMP_GM_LA import show_graph_edges_in_solution, show_LA_arcs_in_solution

epsilon = 0.00001


def build_subproblem(omega_r_plus, omega_y_l, P_hat, E_hat, I_hat, l):
    """
    Returns a tuple `(sub_graph, sub_P)` representing a subproblem for an index `l` in `Omega_r`.

    `sub_graph` is list of graphs in the form (Edges, Nodes); sub_P is a list of dictionaries of LA-Arcs (keyed by (u, v, d)).
    """
    sub_P = copy.deepcopy(P_hat)
    sub_P[l] = omega_y_l[l]

    sub_graph = list(zip(E_hat, I_hat))
    sub_graph[l] = omega_r_plus[l]

    return sub_graph, sub_P


def update_nascent_sets(model, sub_graphs, sub_arcs, x_p, x_ij):
    """
    Updates `P_hat`, `E_hat`, and `I_hat`to contain only the active terms in `x_p` and `x_ij`.
    """
    new_P_hat = []
    new_E_hat = []
    new_I_hat = []
    for l, omega_Y in enumerate(sub_arcs):
        new_P_hat.append(dict())
        for y in omega_Y:
            for arc in omega_Y[y]:
                if model.getSolution(x_p[l][arc.id]) > 0:
                    if y in new_P_hat[l]:
                        new_P_hat[l][y].append(arc)
                    else:
                        new_P_hat[l][y] = [arc]

    for l, (edges, nodes) in enumerate(sub_graphs):
        new_E_hat.append(set())
        new_I_hat.append(set())
        sorted_edges = sorted(edges, key=lambda E: (
            E[0].u.id, E[1].u.id, E[0].cap_remain))

        for (i, j) in sorted_edges:
            if model.getSolution(x_ij[l][i.name, j.name]) > 0:
                new_E_hat[l].add((i, j))
                new_I_hat[l].add(i)
                new_I_hat[l].add(j)

        new_I_hat[l] = sorted(new_I_hat[l], key=node_sort)

    return new_P_hat, new_E_hat, new_I_hat


def easy_PGM():
    """
    Solves CVRP using the easy-PGM method.
    """
    # LOAD PROBLEM DATA
    data_set = "A-n32-k5.vrp"
    MYDIVISOR = 20
    NUM_LA_NEIGHBORS = 0
    CUSTOMER_SIZE_LIMIT = 15
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, MYDIVISOR, NUM_LA_NEIGHBORS, CUSTOMER_SIZE_LIMIT)

    omega_y = find_LA_arcs(customers, end_depot, capacity)

    # INITIALIZE ARRAYS
    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]
    omega_r_plus = []

    beta = compute_beta(omega_r[0], customers)
    omega_y_l = [compute_omega_y_l(beta, omega_y)]
    P_hat = [copy.deepcopy(omega_y_l[0])]
    (edges, nodes) = create_LA_arc_graph(omega_y_l[0], beta, capacity)
    E_hat = [copy.deepcopy(edges)]
    I_hat = [copy.deepcopy(nodes)]
    # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
    omega_r_plus = [(edges, nodes)]

    continue_iter = True
    best_LP_obj = 999999

    while continue_iter:
        # SOLVE ALL SUBPROBLEMS
        did_improve = False
        for l in reversed(range(len(omega_r))):
            sub_graphs, sub_arcs = build_subproblem(
                omega_r_plus, omega_y_l, P_hat, E_hat, I_hat, l)
            # for l2 in reversed(range(len(omega_r))):
            #     print(f"\tLen of sub_arcs[{l2}] = {len(sub_arcs[l2])}")
            model, cover_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                sub_graphs, sub_arcs, customers, start_depot, end_depot)

            model.optimize()
            # show_LA_arcs_in_solution(x_p, model)
            # show_graph_edges_in_solution(x_ij, model)
            sub_obj = model.getObjVal()
            if sub_obj < best_LP_obj:
                print(
                    f"Model Improved for subproblem l = {l}, obj val = {sub_obj}")
                did_improve = True
                best_LP_obj = sub_obj
                P_hat, E_hat, I_hat = update_nascent_sets(
                    model, sub_graphs, sub_arcs, x_p, x_ij)

        # GENERATE NEW COLUMN
        if did_improve == False:
            new_route, rc = generate_col(
                model, cover_constrs, customers, start_depot, end_depot, capacity)
            print(f"Reduced Cost of new route: {rc}")

            if rc > -epsilon:
                continue_iter = False
            else:
                omega_r.append(new_route)
                beta = compute_beta(new_route, customers)
                omega_y_l.append(compute_omega_y_l(beta, omega_y))
                omega_r_plus.append(create_LA_arc_graph(
                    omega_y_l[-1], beta, capacity))
                P_hat.append(copy.deepcopy(omega_y_l[-1]))
                E_hat.append(copy.deepcopy(omega_r_plus[-1][0]))
                I_hat.append(copy.deepcopy(omega_r_plus[-1][1]))

    model.controls.outputlog = 1
    model.optimize()


easy_PGM()
