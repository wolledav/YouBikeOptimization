import json
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

    unloaded_matrix = [[0 for _ in range(steps_cnt)] for _ in range(n)]

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



if __name__ == "__main__":
    instance = "data/instances_v4/weekly_21/weekly_2025-03-24_min_total.json"
    solution = "results/v4_cb/weekly_21/min_total/weekly_2025-03-24_min_total.json"

    unloaded_matrix = get_unloaded_matrix(instance, solution)

