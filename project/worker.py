import os
import time
import shutil
import json

import numpy as np
import pandas as pd
import math
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
def create_task():#shift_names, num_resources, min_working_hours, max_resting):

    # 0. Load data
    shutil.copyfile("./tmp/data", f'./tmp/{current_task.request.id}')
    shutil.copyfile("./tmp/meta", f'./tmp/{current_task.request.id}_meta')

    input_csv_path = './tmp/{current_task.request.id}'
    input_meta_path = './tmp/{current_task.request.id}_meta'
    output_dir = '..'
    mzp = MultiZonePlanner(input_csv_path, input_meta_path, output_dir)
    mzp.schedule()
    mzp.roster()
    mzp.roster_postprocess()
    exit()

    with open(f'./tmp/{current_task.request.id}_meta', "r") as f:
        meta_info = json.load(f)

    HMin = 60
    DayH = 24
    # todo: fix hardcoded Days number
    NDays = 31
    shift_names = meta_info['shift_names'].split(',')
    shifts_coverage = get_shift_coverage(shift_names)

    # 1. Calculate required positions, based on input .csv
    df = pd.read_csv(f'./tmp/{current_task.request.id}')
    df['positions'] = df.apply(lambda row: required_positions(row['call_volume'], row['aht'], 15, row['art'], row['service_level']), axis=1)

    min_date = get_datetime(min(df['tc']))
    max_date = get_datetime(max(df['tc']))
    days = (max_date - min_date).days + 1
    date_diff = get_datetime(df.iloc[1]['tc']) - get_datetime(df.iloc[0]['tc'])
    step_min = int(date_diff.total_seconds() / HMin)
    
    ts = int(HMin / step_min)

    df['target_positions'] = df['positions']   # persist positions for future use
    ratio = 1.0          # this is a starting resource scaling -> trying to schedule with required coverage

    # downgrade resource requirements on each iteration according to the configured percentage
    # on every failed operation will be reduce required resource by some % of original
    resources_degradation = list(meta_info['resources_degradation'])
    for ratio in resources_degradation:
        print(f'==================================')
        print(f'Solving with positions ratio = {ratio}')
        df['positions'] = df['target_positions'].apply(lambda x: int(x*ratio))

        required_resources = []
        for i in range(days):
            df0 = df[i * DayH * ts : (i + 1) * DayH * ts]
            required_resources.append(df0['positions'].tolist())

        print('Scheduling started')
        scheduler = MinAbsDifference(num_days = days,  # S
                                     periods = DayH * ts,  # P
                                     shifts_coverage = shifts_coverage,
                                     required_resources = required_resources,
                                     max_period_concurrency = int(df['positions'].max()),  # gamma
                                     max_shift_concurrency=int(df['positions'].mean()),  # beta
                                     )
        sch_solution = scheduler.solve()

        with open(f'./tmp/{current_task.request.id}_scheduling.json', 'w') as f:
            json.dump(sch_solution, f, indent=2)

        status = sch_solution['status']
        print(f'Scheduling status: {status}')

        if status not in ['OPTIMAL', 'FEASIBLE']:
            return False

        resources = meta_info['resources']
        shift_names = list(shifts_coverage.keys())
        shifts_hours = [int(i.split('_')[1]) for i in shift_names]

        resources_shifts = sch_solution['resources_shifts']
        df1 = pd.DataFrame(resources_shifts)
        df2 = df1.pivot(index='shift', columns='day', values='resources').rename_axis(None, axis=0)
        df2['combined']= df2.values.tolist()
        required_resources = df2['combined'].to_dict()

        banned_shifts = []
        non_sequential_shifts = []
        resources_preferences = []
        resources_prioritization = []

        min_working_hours = meta_info['min_working_hours']
        max_resting = meta_info['max_resting']

        solver = MinHoursRoster(num_days=days,
            resources=resources,
            shifts=shift_names,
            shifts_hours=shifts_hours,
            min_working_hours=min_working_hours,
            max_resting=max_resting,
            non_sequential_shifts=non_sequential_shifts,
            banned_shifts=banned_shifts,
            required_resources=required_resources,
            resources_preferences = resources_preferences,
            resources_prioritization = resources_prioritization
            )

        solution = solver.solve()

        status = solution['status']
        print(f'Rostering status: {status}')

        if status in ['OPTIMAL', 'FEASIBLE']:
            with open(f'./tmp/{current_task.request.id}_rostering.json', 'w') as outfile:
                json.dump(solution, outfile, indent=2)

            print(f'Calculating achieved statistics')
            df_out = calculate_achieved_stats(shift_names, solution, df)

            _output_csv_filename = f'./tmp/{current_task.request.id}_achieved_stats'
            df_out.to_csv(_output_csv_filename)

            print(f'Done')

            return True

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
