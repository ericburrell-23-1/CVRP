import pickle
import json
import time
import xpress as xp
from data.read_problem_data import generate_problem, get_primitive_data
from utilities.RCI.identify_violated_inequalities import RCI_preprocessing
from algorithms.jy_opt.compute_beta import compute_beta
from algorithms.jy_opt.RCI import identify_violated_ineqs
from algorithms.jy_opt.jy_opt_2 import jy_Opt_formulator
from algorithms.jy_opt.RMP import build_RMP
# from algorithms.jy_opt.partial_pricing import add_complimentary_column_edges, dual_dict
from algorithms.jy_opt.dijkstra_pricing import add_complimentary_column_edges
from models.lp_models.RMP_GM_LA import convert_to_ILP


def preprocess(data_set):
    customers, start_depot, end_depot, capacity = generate_problem(data_set, 1, 0)
    N, N_plus, demands, costs = get_primitive_data(customers, start_depot)

    cust_node_capacities = {}
    N2_pairs = set()
    for c in N:
        cust_node_capacities[c] = [capacity]
        N2_pairs.add((-1, c))
        N2_pairs.add((c, -2))
    cust_node_capacities[-1] = [capacity]
    cust_node_capacities[-2] = [0]

    initial_route = [start_depot, customers[0], end_depot]
    betas = {}
    betas[0] = compute_beta(initial_route, customers)
    print(f"First Beta: {betas[0]}")

    RCI_data = RCI_preprocessing(customers, start_depot, end_depot, capacity)
    B_matrix, rhs_vector, row_index, col_index, all_N_hat = RCI_data
    jy_RCI = {}
    # rci_count = 0
    # for N_hat_name in all_N_hat:
    #     N_hat = tuple([u.id for u in all_N_hat[N_hat_name].N_hat])
    #     jy_RCI[N_hat] = rhs_vector[N_hat_name]
    #     rci_count += 1
    #     if rci_count > 29:
    #         break

    uv_edge_dict = {}

    return customers, start_depot, end_depot, capacity, cust_node_capacities, N, N_plus, N2_pairs, demands, costs, betas, RCI_data, jy_RCI, uv_edge_dict



def make_jy_opt_input(data_set):
    customers, start_depot, end_depot, capacity, cust_node_capacities, N, N_plus, N2_pairs, demands, costs, betas, RCI_data, jy_RCI, uv_edge_dict = preprocess(data_set)
    outputs = (N_plus, N, cust_node_capacities, betas, N2_pairs, jy_RCI, demands, uv_edge_dict, costs, capacity)
    print(f"N_plus type: {type(N_plus)}")
    print(f"N type: {type(N)}")
    print(f"cust_node_capacities type: {type(cust_node_capacities)}")
    print(f"betas type: {type(betas)}")
    print(f"N2_pairs type: {type(N2_pairs)}")
    print(f"jy_RCI type: {type(jy_RCI)}")
    print(f"demands type: {type(demands)}")
    print(f"uv_edge_dict type: {type(uv_edge_dict)}")
    print(f"costs type: {type(costs)}")
    print(f"capacity type: {type(capacity)}")

    data = {
        "N_plus": N_plus, 
        "N": N, 
        "cust_node_capacities": cust_node_capacities,
        "betas": betas,
        "N2_pairs": list(N2_pairs),
        "jy_RCI": jy_RCI,
        "demands": demands,
        "uv_edge_dict": uv_edge_dict,
        "costs": costs,
        "capacity": capacity
    }

    # with open('jy_inputs.json', 'w') as f:
    #     json.dump(data, f)

    with open('jy_inputs.pkl', 'wb') as f:
        pickle.dump(outputs, f)

    print("Outputs printed to jy_inputs")

def read_jy_opt_input():
    # Load the saved outputs from the file
    with open('.\jy_inputs.pkl', 'rb') as f:
        loaded_outputs = pickle.load(f)

    (N, N_plus, cust_node_capacities, betas, N2_pairs, jy_RCI, demands, uv_edge_dict, costs, capacity) = loaded_outputs

    print("uv_edge_dict:", uv_edge_dict)
    


def use_jy_opt(data_set):
    customers, start_depot, end_depot, capacity, cust_node_capacities, N, N_plus, N2_pairs, demands, costs, betas, RCI_data, jy_RCI, uv_edge_dict = preprocess(data_set)
    opt = jy_Opt_formulator(N, N_plus, cust_node_capacities, betas, N2_pairs, jy_RCI, demands, uv_edge_dict, costs, capacity)
    uv_edge_dict = opt.dict_uv_2_uv_edge

    rmp, vars, constrs = build_RMP(opt)

    rmp.optimize()
    continue_opt = True
    continue_pgm = True
    last_beta = 0

    while continue_opt:
        continue_opt = False
        while continue_pgm:
            op_start = time.time()
            # continue_pgm = add_complimentary_column_edges(rmp, betas[last_beta], constrs, N, demands, capacity, N2_pairs, costs, cust_node_capacities)
            continue_pgm = add_complimentary_column_edges(rmp, betas[last_beta], N, demands, capacity, costs, constrs, N2_pairs, cust_node_capacities, jy_RCI)
            print(f"Partial pricing took {round(time.time() - op_start, 3)} sec.")

            if continue_pgm:
                op_start = time.time()
                opt = jy_Opt_formulator(N, N_plus, cust_node_capacities, betas, N2_pairs, jy_RCI, demands, uv_edge_dict, costs, capacity)
                print(f"Building opt took {round(time.time() - op_start, 3)} sec.")
                op_start = time.time()
                rmp, vars, constrs = build_RMP(opt)
                print(f"Building rmp took {round(time.time() - op_start, 3)} sec.")

                op_start = time.time()
                rmp.optimize()
                print(f"Solving LP took {round(time.time() - op_start, 3)} sec.")
                print(f"RMP obj val: {round(rmp.getObjVal(), 2)}")

                # CHECK FOR RCI
                op_start = time.time()
                new_rci = identify_violated_ineqs(rmp, vars, RCI_data, N)
                print(f"Checking RCI took {round(time.time() - op_start, 3)} sec.")
                if len(new_rci) > 0:
                    op_start = time.time()
                    print(f"{len(new_rci)} RCI constraints being added")
                    jy_RCI.update(new_rci)
                    opt = jy_Opt_formulator(N, N_plus, cust_node_capacities, betas, N2_pairs, jy_RCI, demands, {}, costs, capacity)
                    uv_edge_dict = opt.dict_uv_2_uv_edge
                    rmp, vars, constrs = build_RMP(opt)

                    rmp.optimize()
                    print(f"Adding RCI and solving took {round(time.time() - op_start, 3)} sec.")
                    print(f"RMP obj val: {round(rmp.getObjVal(), 2)}")


        # COLUMN GEN
        # IF NEGATIVE RC
            # UPDATE AND OPTIMIZE AGAIN
        # ELSE
            # BREAK

    # CONVERT TO ILP
    # FINAL OPTIMIZATION
    convert_to_ILP(rmp)
    rmp.controls.outputlog = 1
    rmp.optimize()


    show_sol(rmp, vars)
        # make_input = input("Make Input? (Y) or {any}")

        # if make_input == "Y" or make_input == "y":
        #     outputs = (N, N_plus, cust_node_capacities, betas, N2_pairs, jy_RCI, demands, {}, costs, capacity)
        #     with open('jy_inputs.pkl', 'wb') as f:
        #         pickle.dump(outputs, f)

    


    

def show_sol(rmp, vars):
    for var_name in vars:
        var = vars[var_name]

        sol = rmp.getSolution(var)
        if sol > 0.0001:
            print(f"Var {var_name} has value {sol}")





# # BUILD JY OPT
# jy_opt = jy_Opt_formulator(N_plus, N, cust_node_capacities, betas, N2_pairs, jy_RCI, demands, uv_edge_dict, costs, capacity)
# uv_edge_dict = jy_opt.dict_uv_2_uv_edge
    

























# SET UP MODEL AND SOLVE TO FIND FIRST ROUND OF RCI CONSTRS
    # BUILD XP MODEL
# model = xp.problem()
# edge_vars = model.getVariable()
#     # OPTIMIZE IT
# model.optimize()

# FIND RCI
# new_RCIs = identify_violated_ineqs(model, edge_vars, RCI_data, customers, end_depot)
# for (lhs_terms, rhs_val, N_hat) in new_RCIs:
#     jy_RCI[N_hat] = rhs_val

