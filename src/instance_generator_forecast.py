import sqlite3
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import json
import os
import matplotlib.pyplot as plt
from utils import fetch_stations

from config import cfg

# ---------------------------------------
# Configuration
# ---------------------------------------
db_path = "./youbike_data.db"
time_of_interest_start = cfg.instance_time_start
time_of_interest_end = cfg.instance_time_end
output_dir = "./data/instances"
os.makedirs(output_dir, exist_ok=True)

default_station = {
    "sno": "unknown_sno",
    "snaen": "Unknown Station",
    "sareaen": "Unknown District",
    "latitude": 0.0,
    "longitude": 0.0,
    "capacity": 10,
    "s_init": 0,
    "s_goal": 0,
    "coords": [0.0, 0.0],
    "predicted_demand": [0] * 24  # 24 hours of zero demand
}


# Fetch stations data
df_stations = fetch_stations(time_of_interest_start, time_of_interest_end, db_path)

def load_and_preprocess_station(station_id):
    conn = sqlite3.connect(db_path)
    query = f"""
    SELECT *
    FROM youbike_data
    WHERE sno = '{station_id}'
    ORDER BY mday ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Ensure `mday` is in datetime format for resampling
    df['mday'] = pd.to_datetime(df['mday'])
    df = df.set_index('mday')

    # Drop non-numeric columns
    non_numeric_cols = df.select_dtypes(exclude=[np.number]).columns
    df = df.drop(columns=non_numeric_cols, errors='ignore')

    # Resample and fill missing values
    df = df.resample('1h').mean().ffill()

    # Ensure `capacity` is present
    if 'capacity' not in df.columns:
        global df_stations
        cap = df_stations.loc[df_stations['sno'] == station_id, 'capacity']
        if len(cap) > 0:
            capacity = cap.iloc[0]
        else:
            capacity = df['available_rent_bikes'].max()  # Fallback guess
        df['capacity'] = capacity
    else:
        capacity = df['capacity'].mean()

    # Compute demand
    demands = []
    prev_bikes = None
    prev_demand = 0
    for t in df.index:
        curr_bikes = df.at[t, 'available_rent_bikes']
        if prev_bikes is None:
            demand = 0
        else:
            raw_demand = prev_bikes - curr_bikes
            if curr_bikes == 0:
                if prev_bikes > 0:
                    demand = prev_bikes
                else:
                    demand = prev_demand if prev_demand > 0 else 1
            elif curr_bikes == capacity:
                if prev_bikes < capacity:
                    demand = prev_bikes - capacity
                else:
                    demand = prev_demand if prev_demand < 0 else -1
            else:
                demand = raw_demand

        demands.append(demand)
        prev_bikes = curr_bikes
        prev_demand = demand

    df['demand'] = demands
    return df


def predict_station_demand_naive(station_id, forecast_date=None):
    df = load_and_preprocess_station(station_id)
    if df.empty:
        return [0] * 24

    if forecast_date is None:
        last_date = df.index[-1].date()
        forecast_date = (pd.to_datetime(last_date) + pd.Timedelta(days=1)).date()

    forecast_start = pd.to_datetime(forecast_date)
    forecast_end = forecast_start + pd.Timedelta(days=7, hours=23)
    hours = pd.date_range(start=forecast_start, end=forecast_end, freq='1H')

    predicted_values = []
    for hour in hours:
        prev_day = hour - pd.Timedelta(days=1)
        prev_week = hour - pd.Timedelta(days=7)

        if (prev_day in df.index) and (prev_week in df.index):
            val_prev_day = df.loc[prev_day, 'demand']
            val_prev_week = df.loc[prev_week, 'demand']
            pred = (val_prev_day + val_prev_week) / 2.0
            predicted_values.append(float(pred))
        else:
            predicted_values.append(0.0)

    return predicted_values

def find_optimal_starting_point(hourly_demands, station_capacity):
    best_s = None
    best_score = float('inf')

    for s in range(0, station_capacity + 1):
        inventory = s
        score = 0

        for demand in hourly_demands:
            inventory -= demand
            if inventory < 0:
                score += abs(inventory)
                inventory = 0
            elif inventory > station_capacity:
                score += (inventory - station_capacity)
                inventory = station_capacity

        if score < best_score:
            best_score = score
            best_s = s

    return {"best_starting_inventory": best_s, "score": best_score}

def get_station_capacity(df, sno, default_capacity=10):
    matching_rows = df.loc[df["sno"] == sno]
    if not matching_rows.empty:
        return int(matching_rows["capacity"].values[0])
    else:
        print(f"Warning: Station {sno} not found in df_stations. Using default capacity.")
        return default_capacity

# Compute demands and balance s_init and s_goal
predicted_demands = {}
for sno in df_stations['sno']:
    hourly_demands = predict_station_demand_naive(sno)
    cap = get_station_capacity(df_stations, sno)
    starting_point = find_optimal_starting_point(hourly_demands, cap)
    predicted_demands[sno] = starting_point

total_s_init = df_stations['s_init'].sum()
total_s_goal = sum(predicted_demands[sno]['best_starting_inventory'] for sno in df_stations['sno'])

if total_s_goal != total_s_init:
    discrepancy = total_s_init - total_s_goal
    print(f"Balancing discrepancy: {discrepancy}")

    for sno in df_stations['sno']:
        if discrepancy == 0:
            break
        adjustment = np.sign(discrepancy)
        predicted_demands[sno]['best_starting_inventory'] += adjustment
        discrepancy -= adjustment

# Generate instance data
stations = []
for i, sno in enumerate(df_stations['sno']):
    row = df_stations[df_stations['sno'] == sno]
    station = {
        "id": i,
        "true_id": sno,
        "station_name": row['snaen'].values[0],
        "capacity": int(row['capacity'].values[0]),
        "district": row['sareaen'].values[0],
        "s_init": int(row['s_init'].values[0]),
        "s_goal": int(predicted_demands[sno]['best_starting_inventory']),
        "coords": [row['latitude'].values[0], row['longitude'].values[0]],
        "predicted_demand": predicted_demands[sno]
    }
    stations.append(station)

distance_csv_path = "distance_matrix.csv"
df_distances = pd.read_csv(distance_csv_path, header=0)
# stations = df_distances.columns.tolist()
distance_matrix = df_distances.values.tolist()
df_distances.index = df_distances.columns

distance_matrix = []
for i, sno in enumerate(df_stations['sno']):
    surr = []
    for j, sno_2 in enumerate(df_stations['sno']):
        distance = int(df_distances[sno][sno_2])
        surr.append(distance)
    distance_matrix.append(surr)

instance = {
    "stations": stations,
    "distances": distance_matrix,
    "vehicles": {
        "count": 2,
        "capacity": 20
    }
}

name = f"test_{time_of_interest_start}_{time_of_interest_end}"
output_file = f"{output_dir}/instance_forecast_{name}.json"
with open(output_file, "w") as f:
    json.dump(instance, f, indent=4)

print(f"Instance saved to {output_file}")
