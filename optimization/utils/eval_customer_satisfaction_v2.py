import json

instance = "data/instances_v4/weekly_21/weekly_2025-03-24_min_total.json"
solution = "results/v4_cb/weekly_21/min_total/weekly_2025-03-24_min_total.json"

instance_data = {}
with open(instance, 'r') as f:
    instance_data = json.load(f)

solution_data = {}
with open(solution, 'r') as f:
    solution_data = json.load(f)

# Simulate the rebalancing
routes = solution_data['routes']
for route in routes:
    print(route)
    break

# TODO implement get_inventories_with_rebalancing 
