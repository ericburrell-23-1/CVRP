from algorithms.basic_cg import solve_MP_with_CG
from algorithms.LA_GM import solve_MP_GM_LA
from algorithms.PGM_easy_edge import PGM_easy_edge
# from algorithms.PGM_last_graph import PGM_last_graph
# from algorithms.time_limited_algs import PGM_last_graph, PGM_easy_edge, PGM_last_graph_no_RCI, PGM_easy_edge_no_RCI, time_limited_CG
from algorithms.partial_pricing_algs import CG_partial_pricing

from data.generate_report import generate_report


# solve_MP_with_CG("cust-N100.vrp")



PGM_easy_edge("cust-N100.vrp", 0)

# PGM_last_graph("cust-N80.vrp", 0)

# PGM_last_graph("cust-N100.vrp", 0)

# PGM_last_graph_no_RCI("cust-N100.vrp", 0)

# PGM_easy_edge_no_RCI("cust-N100.vrp", 0)

# CG_partial_pricing("cust-N50.vrp")

# time_limited_CG("cust-N100.vrp")


# generate_report('./data/test_results/time_limit_CG_partial_pricing.csv', 'output_report.csv')











# solve_MP_GM_LA("A-n32-k5.vrp", 0)