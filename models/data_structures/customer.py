import numpy as np


class Customer:
    def __init__(self, id: str, x: float, y: float, demand: int):
        self.id = id
        self.x = x
        self.y = y
        mydivisor = 20
        self.demand = np.ceil(demand / mydivisor)
