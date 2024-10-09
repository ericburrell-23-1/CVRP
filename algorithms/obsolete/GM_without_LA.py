from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.compute_beta import compute_beta, create_graph_from_beta
from models.data_structures.route import Route
from models.lp_models.RMP_GM import create_RMP_GM_model, create_RMP_GM_ILP_model
from models.data_structures.customer import Customer


epsilon = 0.00001

def solve_MP_CG_GM():
    data_set = "A-n32-k5.vrp"
    MYDIVISOR = 20
    NUM_LA_NEIGHBORS = 8
    CUSTOMER_SIZE_LIMIT = 200
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, MYDIVISOR, NUM_LA_NEIGHBORS, CUSTOMER_SIZE_LIMIT)

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]

    beta = compute_beta(omega_r[0], customers)
    (edges, nodes) = create_graph_from_beta(beta, capacity)
    omega_r_plus = [(edges, nodes)]

    # SOLVE THE RMP, GENERATE NEW COLUMN, SOLVE AGAIN
    model, cover_constrs = create_RMP_GM_model(
        omega_r_plus, customers, start_depot, end_depot)

    continue_iter = True
    iter_count = 0
    while continue_iter:
        model.optimize()
        # count_constrs(model, customers, omega_r_plus)

        new_route, rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity)

        if rc >= -epsilon:
            print(
                f"Done solving. Non-negative reduced cost: rc = {round(rc, 4)}\n")
            continue_iter = False
        else:
            iter_count += 1
            omega_r.append(new_route)
            beta = compute_beta(new_route, customers)
            print(f"Negative reduced cost: rc = {round(rc, 4)}\n")

            omega_r_plus.append(create_graph_from_beta(beta, capacity))
            model, cover_constrs = create_RMP_GM_model(
                omega_r_plus, customers, start_depot, end_depot)

    model.controls.outputlog = 1
    model.optimize()

#     # ILP_model = create_RMP_GM_ILP_model(
#     #     omega_r_plus, customers, start_depot, end_depot)
#     # ILP_model.optimize()

#     # show_routes_traversed(ILP_model)



# # JULIANS GRAPH MASTER
# from utilities.compute_beta import create_meta_graph, create_family_from_meta_graph
# from debug.RMP import show_routes_traversed

# def solve_MP_CG_GM2():
#     data_set = "A-n32-k5.vrp"
#     mydivisor = 20
#     customers, start_depot, end_depot, capacity = generate_problem(
#         data_set, mydivisor)

#     omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]

#     beta = compute_beta(omega_r[0], customers)
#     meta_edges, nodes = create_meta_graph(
#         customers, start_depot, end_depot, capacity)
#     edges = create_family_from_meta_graph(meta_edges, beta)
#     omega_r_plus = [(edges, nodes)]

#     # SOLVE THE RMP, GENERATE NEW COLUMN, SOLVE AGAIN
#     model = create_RMP_GM_model(
#         omega_r_plus, customers, start_depot, end_depot)

#     continue_iter = True
#     while continue_iter:
#         model.optimize()
#         # count_constrs(model, customers, omega_r_plus)

#         new_route, rc = generate_col(
#             model, customers, start_depot, end_depot, capacity)

#         if rc >= -epsilon:
#             print(f"Done solving. Non-negative reduced cost: rc = {rc}")
#             # beta = compute_beta(new_route, customers)
#             # edges = create_family_from_meta_graph(meta_edges, beta)
#             # check_route_not_in_graph(new_route, edges)
#             continue_iter = False
#         else:
#             omega_r.append(new_route)
#             beta = compute_beta(new_route, customers)
#             edges = create_family_from_meta_graph(meta_edges, beta)
#             # check_route_not_in_graph(new_route, edges)

#             omega_r_plus.append((edges, nodes))
#             model = create_RMP_GM_model(
#                 omega_r_plus, customers, start_depot, end_depot)

#     model.setParam('OutputFlag', 1)
#     model.optimize()

#     ILP_model = create_RMP_GM_ILP_model(
#         omega_r_plus, customers, start_depot, end_depot)
#     ILP_model.optimize()

#     show_routes_traversed(ILP_model)


# solve_MP_CG_GM2()