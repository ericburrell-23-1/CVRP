
class Customer:
    def __init__(self, id: str, x: float, y: float, demand: int):
        self.id = id
        self.x = x
        self.y = y
        self.demand = demand
        self.closest_neighbors = []
        self.LA_neighbors = []

    def __eq__(self, other):
        if isinstance(other, Customer):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Customer(id={self.id}, x={self.x}, y={self.y}, demand={self.demand})"
