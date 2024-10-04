import time
import xpress as xp
from debug.RMP_GM_LA import show_graph_edges_in_solution, show_LA_arcs_in_solution, compute_cost_from_LA_arcs_selected, compute_cost_from_routes_departing_depot, check_coverage_over_arcs, check_reduced_cost_of_gen_col, show_primal_and_duals
from debug.col_gen import check_rc_from_matrix
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.generate_col import generate_col
from utilities.compute_beta import compute_beta, create_LA_arc_graph
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l
from utilities.model_updates.update_LA_GM import add_family_to_model, add_RCI_constrs
from utilities.RCI.identify_violated_inequalities import identify_violated_ineqs, RCI_preprocessing
from models.lp_models.RMP_GM_LA_no_arcs import create_RMP_GM_LA_model
from models.data_structures.customer import Customer


epsilon = 0.00001


# DONT USE THIS ITS PRETTY MUCH THE SAME THING AS GM_WITHOUT_LA BUT BREAKS IF YOU USE LAN > 0

def solve_MP_GM_no_LA(data_set):
    MYDIVISOR = 1
    CUSTOMER_SIZE_LIMIT = 10
    customers, start_depot, end_depot, capacity = generate_problem(
        data_set, MYDIVISOR, 0, CUSTOMER_SIZE_LIMIT)

    customers_by_id = {}
    for u in customers + [start_depot, end_depot]:
        customers_by_id[u.id] = u

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]
    omega_y = find_LA_arcs(customers, end_depot, capacity)
    omega_y_l = []
    omega_R_plus = []

    iter_start_time = time.time()
    for route in omega_r:
        beta = compute_beta(route, customers)
        omega_y_l.append(compute_omega_y_l(beta, omega_y))
        (edges, nodes) = create_LA_arc_graph(omega_y_l[-1], beta, capacity)
        # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")
        omega_R_plus.append((edges, nodes))

    RCI_data = RCI_preprocessing(customers, start_depot, end_depot, capacity)
    RCI_constrs = {}
    for c in customers + [end_depot, start_depot]:
        RCI_constrs[c.id] = set()

    model, cover_constrs, flow_constrs, x_ij = create_RMP_GM_LA_model(
        omega_R_plus, customers, start_depot, end_depot)

    continue_iter = True
    iter_count = 0
    cg_count = 0
    while continue_iter:
        model.optimize()
        new_RCIs = identify_violated_ineqs(model, x_ij, RCI_data, customers, end_depot)
        # show_graph_edges_in_solution(x_ij, model)
        # new_RCIs = {}
        add_RCI_constrs(model, new_RCIs, RCI_constrs)
        model.optimize()
        # show_primal_and_duals(model, x_ij, cover_constrs, RCI_constrs)
        iter_count += 1
        print(f"Model has an LP objective val = {model.getObjVal()}")

        new_route, rc = generate_col(
            model, cover_constrs, customers, start_depot, end_depot, capacity, RCI_constrs)

        if rc >= -epsilon:
            iter_end_time = time.time()
            print(
                f"Done solving. Non-negative reduced cost: rc = {round(rc, 4)}\n")

            continue_iter = False
        else:
            check_rc_from_matrix(model, new_route, x_ij, capacity, flow_constrs)
            cg_count += 1
            omega_r.append(new_route)
            beta = compute_beta(new_route, customers)
            omega_y_l.append(compute_omega_y_l(beta, omega_y))
            omega_R_plus.append(create_LA_arc_graph(
                omega_y_l[-1], beta, capacity))
            add_family_to_model(model, omega_R_plus, omega_y_l, cover_constrs, flow_constrs, x_ij, {})

            print(f"Negative reduced cost: rc = {round(rc, 4)}\n")


    model.controls.outputlog = 1
    model.optimize()
    show_primal_and_duals(model, x_ij, cover_constrs, RCI_constrs)
    print(f"GraphMaster finished with {iter_count} solving iterations, {cg_count} columns generated, in {round(iter_end_time - iter_start_time, 1)} iteration time.")

