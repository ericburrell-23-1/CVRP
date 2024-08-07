from cspy import BiDirectional
from networkx import DiGraph
from numpy import array
from data.read_problem_data import generate_problem


G = DiGraph(directed=True, n_res=1)


data_set = "A-n32-k5.vrp"
customers, start_depot, end_depot, capacity = generate_problem(data_set)

for u in customers:
    G.add_edge("Source", u.id, res_cost=[u.demand], weight=5)
    for v in customers:
        G.add_edge(str(i), str(j), res_cost=array([2]), weight=-1)
max_res, min_res = [capacity], [0]
bidirec = BiDirectional(G, max_res, min_res, direction="both", elementary=True)
bidirec.run()
print(bidirec.path)
