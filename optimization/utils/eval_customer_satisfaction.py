#!/usr/bin/env python3

import json
import os
import numpy as np
import re

from inventory_policies import *

is_mapping = {"proportional": "prop"
        }


# instance = "data/instances_v4/weekly_21/weekly_2025-03-24_proportional.json"

instances_dir = "data/instances_v4/weekly_21/"
policy = "proportional"

instances = os.listdir(instances_dir)

table_data = []

print("name\t\t\ttotal_demand\treal_P_mean\treal_Q_total")

for instance in sorted(instances):
    if policy in instance and "unit" not in instance:
        data = {}
        with open(instances_dir + instance, 'r') as f:
            data = json.load(f)
            
        real_P_max_vals = []
        real_Q_total_vals = []
        real_demand_sums = []

        for station in data['stations']:
            capacity = station['capacity']
            s_goal = station['s_goal']
            ideal_s_goal = station['real_s_goal']

            real_demand = station['real_demand']

            real_inventories = get_inventories(real_demand, s_goal, capacity)

            real_P_max_i = get_P_max(real_demand, real_inventories, capacity)

            real_Q_total_i = get_Q_total(real_demand, real_inventories, capacity)

            real_demand_abs = [abs(d) for d in real_demand]
            real_demand_sum = sum(real_demand_abs)

            real_P_max_vals.append(real_P_max_i)
            real_Q_total_vals.append(real_Q_total_i)
            real_demand_sums.append(real_demand_sum)

        real_P_mean = np.mean(real_P_max_vals)
        real_demand_sum = sum(real_demand_sums)
        real_Q_total = 100 * (1 - sum(real_Q_total_vals) / real_demand_sum)


        match = re.search(r'(\d{4}-\d{2}-\d{2})[^_]*_(\w+)\.json$', instance)
        name = instance.replace(".json", "")
        if match:
            date = match.group(1)
            last_word = is_mapping[match.group(2)]
            name = f"{date}_{last_word}"


        # table_data.append([name, demand_sum, real_P_mean, Q_rel_percent])
        print(f"{name}\t\t{real_demand_sum}\t\t{real_P_mean:.2f}\t\t{real_Q_total:.2f}")