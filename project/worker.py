import os
import time
import shutil
import json

import numpy as np
import pandas as pd
import math
from pathlib import Path
from pyworkforce.rostering.binary_programming import MinHoursRoster
from pyworkforce.scheduling import MinAbsDifference

from celery import Celery
from celery import current_task

from plotter import plot
from pyworkforce.queuing import ErlangC
from pyworkforce.utils.shift_spec import get_shift_coverage, get_shift_colors, decode_shift_spec
from pyworkforce.staffing import MultiZonePlanner

from datetime import datetime
def get_datetime(t):
  return datetime.strptime(t, '%Y-%m-%d %H:%M:%S.%f')

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

def required_positions(call_volume, aht, interval, art, service_level):
  erlang = ErlangC(transactions=call_volume, aht=aht / 60.0, interval=interval, asa=art / 60.0, shrinkage=0.0)
  positions_requirements = erlang.required_positions(service_level=service_level / 100.0, max_occupancy=1.00)
  return positions_requirements['positions']

def position_statistics(call_volume, aht, interval, art, service_level, positions):
    erlang = ErlangC(transactions=call_volume, aht=aht / 60.0, interval=interval, asa=art / 60.0, shrinkage=0.0)

    if (positions > 0):
        achieved_service_level = erlang.service_level(positions, scale_positions=False) * 100
        achieved_occupancy = erlang.achieved_occupancy(positions, scale_positions=False)
        waiting_probability = erlang.waiting_probability(positions=positions) * 100

        return (achieved_service_level, achieved_occupancy, waiting_probability)
    else:
        return (0, 0, 0)

def calculate_achieved_stats(shift_names, rostering_solution, df_csv):
    # todo: fix hardcoded Days number
    HMin = 60
    DayH = 24
    NDays = 31

    # 1. Get all possible shifts with daily coverage
    shifts_coverage = get_shift_coverage(shift_names)

    # 2. Get actual resources assignments per day & calculate the sum of resources
    # initiate daily zero sequences
    daily_demand = []
    for _ in range(NDays):
        # todo: fix hardcoded intervals
        daily_demand.append(np.zeros(96))

    # rostering data contains shoft assigment e.g. 0 0 0 1 1 1 1 1 1 1 1 1 0 0 0 0 0 0 0 0 per resource
    # => just sum everything to get overall day+intervals assignments
    for rs in rostering_solution['resource_shifts']:
        day = rs['day'] # day 1, day 2, ...
        shift = rs['shift']

        shift_array = np.array(shifts_coverage[shift])
        daily_demand[day-1] += np.array(shift_array)

    # 3. Get input csv statistics & recalculate erlangs

    min_date = get_datetime(min(df_csv['tc']))
    max_date = get_datetime(max(df_csv['tc']))
    days = (max_date - min_date).days + 1
    date_diff = get_datetime(df_csv.iloc[1]['tc']) - get_datetime(df_csv.iloc[0]['tc'])
    step_min = int(date_diff.total_seconds() / HMin)

    ts = int(HMin / step_min)
    daily_intervals = DayH * ts

    for day in range(days):
        for i in range(daily_intervals):
            df_csv.loc[day*daily_intervals + i, "achieved_positions"] = daily_demand[day][i]

    df_csv['achieved_positions'] = df_csv['achieved_positions'].astype('int')

    for i in range(len(df_csv)):
        sl, occ, art = position_statistics(df_csv.loc[i, 'call_volume'], df_csv.loc[i, 'aht'], 15, df_csv.loc[i, 'art'], df_csv.loc[i, 'service_level'],
                            df_csv.loc[i, 'achieved_positions'])
        df_csv.loc[i, 'achieved_sl'] = round(sl, 2)
        df_csv.loc[i, 'achieved_occ'] = round(occ, 2)
        df_csv.loc[i, 'achieved_art'] = round(art, 2)


    return df_csv

@celery.task(name="create_task")
def create_task():

    output_dir = f'./tmp/{current_task.request.id}'
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    shutil.copyfile("./tmp/data", f'./tmp/{current_task.request.id}/input')
    shutil.copyfile("./tmp/meta", f'./tmp/{current_task.request.id}/meta')

    input_csv_path = f'./tmp/{current_task.request.id}/input'
    input_meta_path = f'./tmp/{current_task.request.id}/meta'

    df = pd.read_csv(input_csv_path, parse_dates=[0], index_col=0)
    with open(input_meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    mzp = MultiZonePlanner(df, meta, output_dir)
    mzp.solve()

    return True

@celery.task(name="create_schedule")
def create_schedule(shift_names):
    shutil.copyfile("./tmp/data", f'./tmp/{current_task.request.id}')

    HMin = 60
    DayH = 24
    shift_names = shift_names.split(',')
    shifts_coverage = get_shift_coverage(shift_names)

    df = pd.read_csv(f'./tmp/{current_task.request.id}')
    df['positions'] = df.apply(lambda row: required_positions(row['call_volume'], row['aht'], 15, row['art'], row['service_level']), axis=1)

    min_date = get_datetime(min(df['tc']))
    max_date = get_datetime(max(df['tc']))
    days = (max_date - min_date).days + 1
    date_diff = get_datetime(df.iloc[1]['tc']) - get_datetime(df.iloc[0]['tc'])
    step_min = int(date_diff.total_seconds() / HMin)
    
    ts = int(HMin / step_min)
    required_resources = []
    for i in range(days):
        df0 = df[i * DayH * ts : (i + 1) * DayH * ts]
        required_resources.append(df0['positions'].tolist())

    scheduler = MinAbsDifference(num_days = days,  # S
                                 periods = DayH * ts,  # P
                                 shifts_coverage = shifts_coverage,
                                 required_resources = required_resources,
                                 max_period_concurrency = int(df['positions'].max()),  # gamma
                                 max_shift_concurrency=int(df['positions'].mean()),  # beta
                                 )
    solution = scheduler.solve()

    with open(f'./tmp/{current_task.request.id}_scheduling.json', 'w') as f:
        json.dump(solution, f, indent=2)

    return True

@celery.task(name="create_roster")
def create_roster(shifts_info):
    magic = 1.5
    resources = [f'emp_{i}' for i in range(0, int(magic * shifts_info["num_resources"]) )]
    # shifts_spec = get_shift_coverage(shifts_info["shifts"])
    # shift_names = list(shifts_spec.keys())
    # shift_names = shifts_info["shifts"]
    # shift_colors = get_shift_colors(shift_names)
    # shifts_hours = [decode_shift_spec(i).duration for i in shifts_info["shifts"]]
    # shift_step = max([decode_shift_spec(i).step for i in shifts_info["shifts"]])
    shifts_hours = [int(i.split('_')[1]) for i in shifts_info["shifts"]]
    # shift_step = 15

    solver = MinHoursRoster(num_days=shifts_info["num_days"],
        resources=resources,
        shifts=shifts_info["shifts"],
        shifts_hours=shifts_hours,
        min_working_hours=shifts_info["min_working_hours"],
        max_resting=shifts_info["max_resting"],
        non_sequential_shifts=shifts_info["non_sequential_shifts"],
        banned_shifts=shifts_info["banned_shifts"],
        required_resources=shifts_info["required_resources"],
        resources_preferences=shifts_info["resources_preferences"],
        resources_prioritization=shifts_info["resources_prioritization"])

    solution = solver.solve()

    with open(f'./tmp/{current_task.request.id}_rostering.json', 'w') as outfile:
        json.dump(solution, outfile, indent=2)

    # try:
    #     plot(solution, shifts_spec, shift_step, shifts_info["num_days"], shift_colors, shifts_info["resources"], f'./tmp/{current_task.request.id}_image.png', fig_size=(12,5))
    # except ArithmeticError:
    #     print("plot error")

    return True
