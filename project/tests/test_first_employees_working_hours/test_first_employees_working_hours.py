import pytest
import requests
import json
import csv
import time
from datetime import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv, find_dotenv


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

def test_first_employees_working_hours():
    load_dotenv(find_dotenv())

    files = {
        "data_file": open('test_first_employees_working_hours/_data_file_improvisation.csv', 'rb'),
        "meta_file": open('test_first_employees_working_hours/_meta_file_first_employees_working_hours.json', 'rb'),
        "solver_profile_file": open('test_first_employees_working_hours/_solver_profile_file.json', 'rb')
    }
    with open(f'test_first_employees_working_hours/_meta_file_first_employees_working_hours.json', 'r',
              encoding='utf-8') as f:
        meta = json.load(f)

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(30)

    id = (res.json()['id'])
    response = requests.get(os.getenv('urlget') + f'task/{id}/result')
    shifts = response_to_shifts(meta, response)
    maxWorkingHours = meta['employees'][0]['maxWorkingHours']
    minWorkingHours = meta['employees'][0]['minWorkingHours']

    actual_time = len(list(shifts)) * 9 - 22
    assert actual_time <= maxWorkingHours
    assert actual_time >= minWorkingHours
