import copy
import random
from models.data_structures.route import Route
from models.data_structures.customer import Customer


class Node:
    def __init__(self, u: Customer, cap_remain: int):
        self.u = u
        self.cap_remain = cap_remain
        self.name = f"{u.id}_{cap_remain}"

    def __repr__(self):
        return f"Node({self.u}, {self.cap_remain})"

    def __eq__(self, other):
        if isinstance(other, Node):
            return (self.u == other.u) and (self.cap_remain == other.cap_remain)
        return False

    def __hash__(self):
        return hash((self.u, self.cap_remain))


def compute_beta(route: Route, customers: list):
    beta = []
    for c in route.visits:
        beta.append(c)

    customers_to_add = rand_order(set(customers) - set(route.visits), 39)

    for v in customers_to_add:
        for u in v.closest_neighbors:
            if u in beta:
                beta.insert(beta.index(u) + 1, v)
                break

    # print(f"Beta = {[u.id for u in beta]}")
    return beta


def rand_order(customers, seed):
    customers_list = sorted(list(customers), key=lambda c: c.id)

    random.Random(seed).shuffle(customers_list)
    return customers_list


def create_graph_from_beta(beta: list, capacity: int):
    '''
    Creates a GraphMaster graph. Consists of a nodes of the form i = (u_i, d_i) where d_i is the remaining capacity at that node, and recursively draws edges to new nodes j = (u_j, d_j) for a customer u_j that is further along in the ordering beta than u_i, and d_j = d_i - d_u_i. Starting node = (start_depot, capacity). Returns (edges, nodes).
    '''
    edges = set()
    visited = set()
    start_node = Node(beta[0], int(capacity))
    visited.add(start_node)

    def draw_edges_from(node: Node):
        beta_index = beta.index(node.u)
        for v in beta[beta_index + 1:]:
            if node.cap_remain - v.demand >= 0:
                new_node = Node(v, int(node.cap_remain - v.demand))
                if (node, new_node) not in edges:
                    edges.add((node, new_node))
                    # print(f"Edge added ({node.name}, {new_node.name})")
                    if (v.id != "end") and (new_node not in visited):
                        # input(f"Exploring new node {new_node.name}")
                        visited.add(new_node)
                        draw_edges_from(new_node)
                    elif v.id == "end" and (new_node not in visited):
                        visited.add(new_node)

    for v in beta[1:-1]:
        new_node = Node(v, int(start_node.cap_remain - v.demand))
        edges.add((start_node, new_node))
        # print(f"Edge added ({start_node.name}, {new_node.name})")
        visited.add(new_node)
        # print(f"Exploring new node {new_node.name}")
        draw_edges_from(new_node)

    return (edges, sorted(visited, key=node_sort))


def create_LA_arc_graph(omega_y: dict, beta: list, capacity: int):
    '''
    Creates GraphMaster graph, consistent with ordering beta and beta-compliant LA arcs omega_y. Contains edges from starting node (start_depot, capacity) to nodes at each customer (u, capacity - d_u), and then to all other nodes that can be accessed by following an LA arc in omega_y. Returns (edges, nodes).
    '''
    # print("Creating LA arc graph")
    edges = set()
    visited = set()
    start_node = Node(beta[0], int(capacity))
    visited.add(start_node)

    # beta_ids = [u.id for u in beta]
    # print(f"Beta looks like this: {beta_ids}")

    def draw_edges_from(node: Node):
        '''
        Draws edges from current node i = (u_i, d_i) to all new nodes j at (u_j, d_j), where beta.index(u_j) > beta.index(u_i), and d_j = d_i - d_y for some y = (u_i, u_j, d_y) in omega_y.
        '''
        beta_index = beta.index(node.u)
        for v in beta[beta_index + 1:]:
            if round(node.cap_remain - v.demand) >= node.u.demand:
                for d in range(int(node.u.demand), int(round(node.cap_remain - v.demand + 1))):
                    y = (node.u.id, v.id, int(d))
                    if y in omega_y:
                        new_node = Node(v, int(round(node.cap_remain - d)))
                        if (node, new_node) not in edges:
                            edges.add((node, new_node))
                            # print(f"Edge added ({node.name}, {new_node.name})")
                            if (v.id != "end") and (new_node not in visited):
                                # print(f"Exploring new node {new_node.name}")
                                visited.add(new_node)
                                draw_edges_from(new_node)
                            elif v.id == "end" and (new_node not in visited):
                                visited.add(new_node)

    for v in beta[1:-1]:
        new_node = Node(v, int(round(start_node.cap_remain)))
        edges.add((start_node, new_node))
        # print(f"Edge added ({start_node.name}, {new_node.name})")
        visited.add(new_node)
        # print(f"Exploring new node {new_node.name}")
        draw_edges_from(new_node)

    print(f"Graph complete, it has {len(visited)} nodes and {len(edges)} edges.")

    return (edges, sorted(visited, key=node_sort))


def create_meta_graph(customers: list, start_depot: Customer, end_depot: Customer, capacity: int):
    edges = set()
    nodes = []

    source = Node(start_depot, capacity)
    sink = Node(end_depot, 0)
    nodes.append(source)
    for u in customers:
        for d in range(int(u.demand), int(round(capacity + 1))):
            nodes.append(Node(u, d))
    nodes.append(sink)

    for i in nodes[1:-1]:
        edges.add((i, sink))
        edges.add((source, i))
        for j in nodes[1:-1]:
            if j.cap_remain == round(i.cap_remain - i.u.demand):
                edges.add((i, j))

    return edges, nodes


def create_family_from_meta_graph(meta_edges, beta):
    edges = set()

    for i, j in meta_edges:
        if beta.index(i.u) < beta.index(j.u):
            edges.add((i, j))

    return edges


def node_sort(a: Node):
    if a.u.id == "start":
        return (0, a.cap_remain)
    elif a.u.id == "end":
        return (99999, a.cap_remain)
    else:
        return (int(a.u.id), a.cap_remain)
