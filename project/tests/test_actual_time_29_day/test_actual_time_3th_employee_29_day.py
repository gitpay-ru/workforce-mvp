import pytest
import requests
import json
import csv
import time
from datetime import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv, find_dotenv
import pandas as pd

def response_to_shifts(meta, response):

    format = '%d.%m.%y %H:%M'
    shifts_duration = {}
    for s in meta['shifts']:
        shifts_duration[s['id']] = timedelta(minutes=int(s['duration'][:-3]) * 60 + int(s['duration'][-2:]))

    shifts = map(
    lambda x: dict(Employee=str(x['employeeId']),
                   StartDateTime=datetime.strptime(f"{x['shiftDate']} {x['shiftTimeStart']}", format),
                   FinishDateTeme=datetime.strptime(f"{x['shiftDate']} {x['shiftTimeStart']}", format) +
                                  shifts_duration[x['shiftId']],
                   Shift=x['shiftId'])
    , response.json()["campainSchedule"]
)
    return shifts

def test_actual_time_3th_employee_29_day():
    load_dotenv(find_dotenv())

    files = {
        "data_file": open('test_actual_time_29_day/_data_file_improvisation_29_day.csv', 'rb'),
        "meta_file": open('test_actual_time_29_day/_meta_file_actual_time_29_day_one_month.json', 'rb'),
        "solver_profile_file": open('test_actual_time_29_day/_solver_profile_file.json', 'rb')
    }
    with open(f'test_actual_time_29_day/_meta_file_actual_time_29_day_one_month.json', 'r',
              encoding='utf-8') as f:
        meta = json.load(f)

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(30)

    id = (res.json()['id'])
    response = requests.get(os.getenv('urlget') + f'task/{id}/result')
    shifts = response_to_shifts(meta, response)

    df = pd.DataFrame(shifts)
    employees1 = df['Employee'].value_counts()[2] * 8
    employees2 = df['Employee'].value_counts()[1] * 8
    employees3 = df['Employee'].value_counts()[0] * 8
    maxWorkingHoursE1 = meta['employees'][0]['maxWorkingHours']
    maxWorkingHoursE2 = meta['employees'][1]['maxWorkingHours']
    maxWorkingHoursE3 = meta['employees'][2]['maxWorkingHours']
    minWorkingHoursE1 = meta['employees'][0]['maxWorkingHours']
    minWorkingHoursE2 = meta['employees'][1]['maxWorkingHours']
    minWorkingHoursE3 = meta['employees'][2]['maxWorkingHours']
    assert maxWorkingHoursE1 == employees1
    assert minWorkingHoursE1 <= employees1
    assert maxWorkingHoursE2 == employees2
    assert minWorkingHoursE2 <= employees2
    assert maxWorkingHoursE3 == employees3
    assert minWorkingHoursE3 <= employees3
