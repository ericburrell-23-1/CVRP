import random

def generate_cvrp_data(num_customers):
    # Header information
    header = f"""
NAME : Custom-CVRP
COMMENT : Custom generated data set
TYPE : CVRP
DIMENSION : {num_customers + 1}
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 10
NODE_COORD_SECTION
"""

    # Generating coordinates (x, y between 1-200) and writing node coordinates section
    node_coord_section = ""
    for i in range(1, num_customers + 2):
        x = random.randint(1, 99)
        y = random.randint(1, 99)
        node_coord_section += f" {i} {x} {y}\n"

    # Generating demand section with customer 1 having a demand of 0, rest 1-3
    demand_section = "DEMAND_SECTION\n"
    for i in range(1, num_customers + 2):
        demand = 0 if i == 1 else random.randint(1, 3)
        demand_section += f" {i} {demand}\n"

    # Depot section
    depot_section = """DEPOT_SECTION
 1
 -1
EOF
"""

    return header + node_coord_section + demand_section + depot_section

# Generate data for 500 customers
cvrp_data_500_customers = generate_cvrp_data(100)

# Save the data to a file
with open('cust_N100.txt', 'w') as file:
    file.write(cvrp_data_500_customers)

print("100-customer CVRP data has been saved to 'cvrp_500_customers.txt'")
