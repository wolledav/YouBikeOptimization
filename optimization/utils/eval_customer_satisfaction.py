#!/usr/bin/env python3

import json
import os
import numpy as np

instance = "data/instances_v4/naive_2024-12-28_duration/NTU.json"
demand_timestep = 300 # seconds
period = 24 * 60 * 60 # seconds
steps = period // demand_timestep
print(steps)

data = {}
with open(instance, 'r') as f:
    data = json.load(f)
    for st in data['stations']:
        capacity = st["capacity"]
        random_demands = np.random.randint(-capacity, capacity + 1, size=steps).tolist()
        st["demands"] = random_demands

    data["constants"]["demand_timestep"] = demand_timestep
    
print(data)