#!/usr/bin/env python3

import json
import os
import numpy as np
import re

from inventory_policies import *
from tabulate import tabulate
import math


def get_unloaded_matrix(instance, solution):
    """
    Create a matrix of unloaded items for each station and time step.
    :param instance: path to the instance file
    :param solution: path to the solution file
    :return: unloaded matrix
    """
    instance_data = {}
    with open(instance, 'r') as f:
        instance_data = json.load(f)

    solution_data = {}
    with open(solution, 'r') as f:
        solution_data = json.load(f)

    # Create rebalancing matrix
    n = len(instance_data['stations'])
    steps_cnt = len(instance_data['stations'][0]['demand'])
    timestep = instance_data["constants"]["demand_timestep"]
    parking_time = instance_data["constants"]["parking_time"]
    loading_time = instance_data["constants"]["loading_time"]

    print("n:", n)
    print("steps_cnt:", steps_cnt)
    print("timestep:", timestep)

    unloaded_matrix = [[0 for _ in range(steps_cnt + 1)] for _ in range(n)]

    # Simulate the rebalancing
    routes = solution_data['routes']
    for route in routes:
        # print("route:", route)
        duration = route['duration']
        depot = route['depot_id']
        station_cur = route['route'][0]
        lload_prev = 0
        lload_cur = route['leaving_load'][0]
        unloaded_cur = lload_prev - lload_cur
        t_cur = instance_data['depots'][depot]["dists_from_depot"][station_cur] + parking_time + abs(unloaded_cur) * loading_time
        t_cur_step = math.ceil(t_cur / timestep)
        unloaded_matrix[station_cur][t_cur_step] += unloaded_cur

        # print("depot:", depot)
        # print("station_cur:", station_cur)
        # print("lload_cur:", lload_cur)
        # print("t:", t_cur)
        # print()

        for i in range(1, len(route['route'])):
            station_prev = station_cur
            station_cur = route['route'][i]
            lload_prev = lload_cur
            lload_cur = route['leaving_load'][i]
            unloaded_cur = lload_prev - lload_cur
            t_cur = t_cur + instance_data['distances'][station_prev][station_cur] + parking_time + abs(unloaded_cur) * loading_time
            t_cur_step = math.ceil(t_cur / timestep)
            unloaded_matrix[station_cur][t_cur_step] += unloaded_cur
            # print(station_cur, t_cur_step, unloaded_cur)

        # check final arrival time
        t_cur = t_cur + instance_data['depots'][depot]["dists_to_depot"][station_cur] # final time in depot
        assert t_cur == duration

    return unloaded_matrix




is_mapping = {"proportional": "prop",
              "min_total": "Q_total",
              "min_peak": "P_mean",
              "nochange": "no_change"
        }

instances_dir = "data/instances_v4/weekly_21/"

solution_dir = "results/v4_cb/weekly_21/min_total/"
policy = "min_total"

solution_dir = "results/v4_cb/weekly_21/min_peak/"
policy = "min_peak"

solution_dir = "results/v4_cb/weekly_21/proportional/"
policy = "proportional"

nochange = True

# instances_dir = "data/instances_v4/weekly_nochange/"
# solution_dir = "results/v4_cb/weekly_21/proportional/"

instances = os.listdir(instances_dir)

table_data = []


for instance in sorted(instances):
    if policy in instance and "unit" not in instance:
        instance_path = instances_dir + instance
        solution_path = solution_dir + instance

        print("Processing: ", instance_path)
        print("with solution: ", solution_path)
        print()

        data = {}
        with open(instance_path, 'r') as f:
            data = json.load(f)

        unloaded_matrix = get_unloaded_matrix(instance_path, solution_path)
            
        real_demand_sums = [] # real demands from historical data

        ideal_P_max_vals = []
        ideal_Q_total_vals = []
        real_P_max_vals = []
        real_Q_total_vals = []
        real2_P_max_vals = []
        real2_Q_total_vals = []

        for station in data['stations']:
            s_id = station['id']
            capacity = station['capacity']
            real_demand = station['real_demand']
            unloadings = unloaded_matrix[s_id]

            pred_s_goal = station['s_goal']         # based on predicted demands (real)
            ideal_s_goal = station['real_s_goal']   # based on historical demands (ideal)
            if nochange:
                pred_s_goal = station['s_init']
                ideal_s_goal = station['s_init']

            # perfect prediction & perfect rebalancing
            ideal_inventories = get_inventories(real_demand, ideal_s_goal, capacity)
            ideal_P_max_i = get_P_max(real_demand, ideal_inventories, capacity)
            ideal_Q_total_i = get_Q_total(real_demand, ideal_inventories, capacity)
            ideal_P_max_vals.append(ideal_P_max_i)
            ideal_Q_total_vals.append(ideal_Q_total_i)

            # real prediction & perfect rebalancing
            real_inventories = get_inventories(real_demand, pred_s_goal, capacity)
            real_P_max_i = get_P_max(real_demand, real_inventories, capacity)
            real_Q_total_i = get_Q_total(real_demand, real_inventories, capacity)
            real_P_max_vals.append(real_P_max_i)
            real_Q_total_vals.append(real_Q_total_i)

            # real prediction & real rebalancing
            real2_inventories = get_inventories_w_unloading(real_demand, pred_s_goal, capacity, unloadings)
            real2_P_max_i = get_P_max(real_demand, real2_inventories, capacity)
            real2_Q_total_i = get_Q_total(real_demand, real2_inventories, capacity)
            real2_P_max_vals.append(real2_P_max_i)
            real2_Q_total_vals.append(real2_Q_total_i)

            real_demand_abs = [abs(d) for d in real_demand]
            real_demand_sum = sum(real_demand_abs)
            real_demand_sums.append(real_demand_sum)

        real_total_demand_sum = sum(real_demand_sums)

        ideal_P_mean = np.mean(ideal_P_max_vals)
        ideal_Q_total = 100 * (1 - sum(ideal_Q_total_vals) / real_total_demand_sum)
        real_P_mean = np.mean(real_P_max_vals)
        real_Q_total = 100 * (1 - sum(real_Q_total_vals) / real_total_demand_sum)
        real2_P_mean = np.mean(real2_P_max_vals)
        real2_Q_total = 100 * (1 - sum(real2_Q_total_vals) / real_total_demand_sum)

        match = re.search(r'(\d{4}-\d{2}-\d{2})[^_]*_(\w+)\.json$', instance)
        name = instance.replace(".json", "")
        if match:
            date = match.group(1)
            last_word = is_mapping[match.group(2)]
            name = f"{date}_{last_word}"
        table_data.append([name, real_total_demand_sum, ideal_P_mean, ideal_Q_total, real_P_mean, real_Q_total, real2_P_mean, real2_Q_total])
        # print(f"{name}\t{real_demand_sum}\t\t{ideal_P_mean:.2f}\t\t{ideal_Q_total:.2f}\t\t{real_P_mean:.2f}\t\t{real_Q_total:.2f}")


# Calculate averages for each column
averages = ["mean"]
for col in range(1, len(table_data[0])):
    col_values = [row[col] for row in table_data if not np.isnan(row[col])]
    averages.append(np.mean(col_values))

# Append averages to table_data
table_data.append(averages)

# 
if nochange:
    for row in table_data:
        row[4] = 'nan'
        row[5] = 'nan'
        row[6] = 'nan'
        row[7] = 'nan'

# Generate LaTeX table with int and float formats
headers = ["Instance", "Total Demand", "Ideal P mean", "Ideal Q total", "Real P mean", "Real Q total", "Real2 P mean", "Real2 Q total"]
floatfmts = (".0f", ".0f", ".2f", ".2f", ".2f", ".2f", ".2f", ".2f")
latex_table = tabulate(table_data, headers, tablefmt="latex", floatfmt=floatfmts)

# Print LaTeX table
print(latex_table)


