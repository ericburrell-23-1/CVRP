from models.data_structures.customer import Customer


class Node:
    def __init__(self, u: Customer, cap_remain: int):
        self.u = u
        self.cap_remain = cap_remain
        self.name = f"{u.id}_{cap_remain}"
        self.successors = dict()
        self.predecessors = dict()

    def __repr__(self):
        return f"Node({self.u}, {self.cap_remain})"

    def __eq__(self, other):
        if isinstance(other, Node):
            return (self.u == other.u) and (self.cap_remain == other.cap_remain)
        return False

    def __hash__(self):
        return hash((self.u, self.cap_remain))
    
    def add_successor(self, succ):
        if succ.u.id in self.successors:
            current_succ = self.successors[succ.u.id]
            if current_succ.cap_remain < succ.cap_remain <= self.cap_remain - self.u.demand:
                self.successors[succ.u.id] = succ
                succ.add_predecessor(self)
                current_succ.remove_predecessor(self.u.id)
        elif succ.cap_remain <= self.cap_remain - self.u.demand:
            self.successors[succ.u.id] = succ

    def add_predecessor(self, pred):
        self.predecessors[pred.u.id] = pred

    def remove_predecessor(self, pred_id):
        self.predecessors[pred_id] = None # NEED TO FULLY DELETE THIS KEY



class GM_graph:
    def __init__(self, nodes_of_u: dict, N2_pairs: set, beta: list):
        self.beta = beta
        self.edges = self.draw_edges(nodes_of_u, N2_pairs)


    def draw_edges(self, nodes_of_u: dict, N2_pairs):
        source = nodes_of_u[self.beta[0].id]
        sink = nodes_of_u[self.beta[-1].id]
        visited = set()

        for u in self.beta[1:-1]:
            for node in nodes_of_u:
                print("work In Progress")




def compute_successors(new_N2: set, nodes_by_u: dict):
    for u_id, v_id in new_N2:
        for node1 in nodes_by_u[u_id]:
            for node2 in nodes_by_u[v_id]:
                node1.add_successor(node2)

    remove_nodes(nodes_by_u)

    
def remove_nodes(nodes_by_u: dict):
    for u_id in nodes_by_u:
        for node in nodes_by_u[u_id]:
            if len(node.predecessors) < 1:
                nodes_by_u[u_id].remove(node)