import os
import time
import shutil
import json
import pandas as pd
import math
from pyworkforce.rostering.binary_programming import MinHoursRoster
from pyworkforce.scheduling import MinRequiredResources

from celery import Celery
from celery import current_task

from plotter import plot
from shift_spec import get_shift_coverage, get_shift_colors, decode_shift_spec

from datetime import datetime
def get_datetime(t):
  return datetime.strptime(t, '%Y-%m-%d %H:%M:%S.%f')

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")



@celery.task(name="create_schedule")
def create_schedule(shift_names):
    shutil.copyfile("./tmp/data", f'./tmp/{current_task.request.id}')

    HMin = 60
    DayH = 24
    shift_names = shift_names.split(',')
    shifts_coverage = get_shift_coverage(shift_names)

    df = pd.read_csv(f'./tmp/{current_task.request.id}')
    min_date = get_datetime(min(df['tc']))
    max_date = get_datetime(max(df['tc']))
    days = (max_date - min_date).days + 1
    date_diff = get_datetime(df.iloc[1]['tc']) - get_datetime(df.iloc[0]['tc'])
    step_min = int(date_diff.total_seconds() / HMin)
    
    ts = int(HMin / step_min)
    required_resources = []
    for i in range(days):
        df0 = df[i * DayH * ts : (i + 1) * DayH * ts]
        required_resources.append(df0['call_volume'].tolist())

    scheduler = MinRequiredResources(num_days = days,  # S
                                 periods = DayH * ts,  # P
                                 shifts_coverage = shifts_coverage,
                                 required_resources = required_resources,
                                 max_period_concurrency = 700,  # gamma
                                 max_shift_concurrency=35,  # beta
                                 )
    solution = scheduler.solve()

    with open(f'./tmp/{current_task.request.id}_scheduling.json', 'w') as f:
        json.dump(solution, f, indent=2)

    return True

@celery.task(name="create_roster")
def create_roster(shifts_info):
    shifts_spec = get_shift_coverage(shifts_info["shifts"])
    shift_names = list(shifts_spec.keys())
    shift_colors = get_shift_colors(shift_names)
    shifts_hours = [decode_shift_spec(i).duration for i in shifts_info["shifts"]]
    shift_step = max([decode_shift_spec(i).step for i in shifts_info["shifts"]])

    solver = MinHoursRoster(num_days=shifts_info["num_days"],
        resources=shifts_info["resources"],
        shifts=shift_names,
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

    try:
        plot(solution, shifts_spec, shift_step, shifts_info["num_days"], shift_colors, shifts_info["resources"], f'./tmp/{current_task.request.id}_image.png', fig_size=(12,5))
    except ArithmeticError:
        print("plot error")

    return True
