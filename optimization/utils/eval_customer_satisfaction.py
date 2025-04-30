#!/usr/bin/env python3

import json
import os
import numpy as np
import re

from inventory_policies import *
from tabulate import tabulate


is_mapping = {"proportional": "prop",
              "min_total": "Q_total",
              "min_peak": "P_mean",
              "nochange": "no_change"
        }


instances_dir = "data/instances_v4/weekly_21/"
policy = "proportional"
# policy = "min_total"
# policy = "min_peak"

# instances_dir = "data/instances_v4/weekly_nochange/"
# policy = "nochange"

instances = os.listdir(instances_dir)

table_data = []


for instance in sorted(instances):
    if policy in instance and "unit" not in instance:
        data = {}
        with open(instances_dir + instance, 'r') as f:
            data = json.load(f)
            
        real_demand_sums = []

        real_P_max_vals = []
        real_Q_total_vals = []
        ideal_P_max_vals = []
        ideal_Q_total_vals = []

        for station in data['stations']:
            capacity = station['capacity']
            s_goal = station['s_goal']
            ideal_s_goal = station['real_s_goal']

            real_demand = station['real_demand']

            real_inventories = get_inventories(real_demand, s_goal, capacity)
            real_P_max_i = get_P_max(real_demand, real_inventories, capacity)
            real_Q_total_i = get_Q_total(real_demand, real_inventories, capacity)
            real_P_max_vals.append(real_P_max_i)
            real_Q_total_vals.append(real_Q_total_i)

            ideal_inventories = get_inventories(real_demand, ideal_s_goal, capacity)
            ideal_P_max_i = get_P_max(real_demand, ideal_inventories, capacity)
            ideal_Q_total_i = get_Q_total(real_demand, ideal_inventories, capacity)
            ideal_P_max_vals.append(ideal_P_max_i)
            ideal_Q_total_vals.append(ideal_Q_total_i)

            real_demand_abs = [abs(d) for d in real_demand]
            real_demand_sum = sum(real_demand_abs)
            real_demand_sums.append(real_demand_sum)

        real_total_demand_sum = sum(real_demand_sums)

        real_P_mean = np.mean(real_P_max_vals)
        real_Q_total = 100 * (1 - sum(real_Q_total_vals) / real_total_demand_sum)
        ideal_P_mean = np.mean(ideal_P_max_vals)
        ideal_Q_total = 100 * (1 - sum(ideal_Q_total_vals) / real_total_demand_sum)

        match = re.search(r'(\d{4}-\d{2}-\d{2})[^_]*_(\w+)\.json$', instance)
        name = instance.replace(".json", "")
        if match:
            date = match.group(1)
            last_word = is_mapping[match.group(2)]
            name = f"{date}_{last_word}"
        table_data.append([name, real_total_demand_sum, ideal_P_mean, ideal_Q_total, real_P_mean, real_Q_total])
        # print(f"{name}\t{real_demand_sum}\t\t{ideal_P_mean:.2f}\t\t{ideal_Q_total:.2f}\t\t{real_P_mean:.2f}\t\t{real_Q_total:.2f}")

# Calculate averages for each column
averages = ["mean"]
for col in range(1, len(table_data[0])):
    col_values = [row[col] for row in table_data if not np.isnan(row[col])]
    averages.append(np.mean(col_values))

# Append averages to table_data
table_data.append(averages)

# 
if policy == "nochange":
    for row in table_data:
        row[4] = 'nan'
        row[5] = 'nan'

# Generate LaTeX table with int and float formats
headers = ["Instance", "Total Demand", "Ideal P mean", "Ideal Q total", "Real P mean", "Real Q total"]
floatfmts = (".0f", ".0f", ".2f", ".2f", ".2f", ".2f")
latex_table = tabulate(table_data, headers, tablefmt="latex", floatfmt=floatfmts)

# Print LaTeX table
print(latex_table)


