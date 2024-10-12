from models.lp_models.RMP_GM_LA import create_RMP_GM_LA_model
from data.read_problem_data import generate_problem
from utilities.initial_omega_r import initialize_omega_r
from utilities.LA_arcs import find_LA_arcs, compute_omega_y_l
from utilities.compute_beta import compute_beta, create_LA_arc_graph
from utilities.RCI.identify_violated_inequalities import RCI_preprocessing
from utilities.PGM.PGM import consistent_N2_arcs, consistent_N2_graphs, pgm_preprocessing

MY_DIVISOR = 1
epsilon = 0.00001


def problem_setup_PP(DATA_SET, NUM_LA_NEIGHBORS):
    customers, start_depot, end_depot, capacity = generate_problem(DATA_SET, MY_DIVISOR, NUM_LA_NEIGHBORS)

    customers_by_id = {}
    for u in customers + [start_depot, end_depot]:
        customers_by_id[u.id] = u

    initial_N2_pairs = set()
    for c in customers:
        initial_N2_pairs.add((start_depot.id, c.id))
        initial_N2_pairs.add((c.id, end_depot.id))

    N2_pairs = [set()]
    N2_pairs[0].update(initial_N2_pairs)

    omega_r = [initialize_omega_r(start_depot, customers, end_depot)[0]]
    omega_y = find_LA_arcs(customers, end_depot, capacity)
    omega_y_l = []
    omega_R_plus = []

    print("Pre-processing RCI...")
    RCI_data = RCI_preprocessing(customers, start_depot, end_depot, capacity)
    RCI_constrs = {}
    for c in customers + [end_depot, start_depot]:
        RCI_constrs[c.id] = set()

    print("Building first graph...")
    route = omega_r[0]
    beta = compute_beta(route, customers)
    omega_y_l.append(compute_omega_y_l(beta, omega_y))

    print("Checking N2 consistent arcs and edges...")
    N2_omega_y_l = consistent_N2_arcs(omega_y_l, N2_pairs, [])
    (edges, nodes) = create_LA_arc_graph(N2_omega_y_l[-1], beta, capacity)
    omega_R_plus.append((edges, nodes))
    N2_omega_R_plus = consistent_N2_graphs(omega_R_plus, N2_pairs, [])

    # print(f"Graph has {len(nodes)} nodes and {len(edges)} edges")


    print("Building xp.problem model...")
    model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p = create_RMP_GM_LA_model(
                N2_omega_R_plus, N2_omega_y_l, customers, start_depot, end_depot)
    
    print("Preprocessing PGM matrix info...")
    PGM_arc_data, PGM_uv_data = pgm_preprocessing(omega_y, customers, end_depot, cover_constrs)
    arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows = PGM_arc_data
    uv_matrix, cost_vector, all_dual_constrs = PGM_uv_data

    return customers, start_depot, end_depot, capacity, RCI_data, RCI_constrs, initial_N2_pairs, N2_pairs, N2_omega_y_l, N2_omega_R_plus, omega_r, omega_y, omega_y_l, omega_R_plus, model, cover_constrs, flow_constrs, consistency_constrs, x_ij, x_p, arc_matrix, arc_row_indices, uv_col_indices, y_arc_rows, uv_matrix, cost_vector, all_dual_constrs, beta

