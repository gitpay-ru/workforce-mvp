import pytest
import requests
import json
import csv
import time
from datetime import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv, find_dotenv

format = '%d.%m.%y %H:%M'

with open('test_actual_time_one_employee_one_month/_data_file_improvisation.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)

with open(f'test_actual_time_one_employee_one_month/_meta_file_actual_time_one_employee_one_month.json', 'r',
          encoding='utf-8') as f:
    meta = json.load(f)

with open('test_actual_time_one_employee_one_month/_solver_profile_file.json', 'r', encoding='utf-8') as f:
    solver = json.load(f)


def response_to_shifts(response):

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

def test_actual_time_one_employee_one_month():
    load_dotenv(find_dotenv())

    files = {
        'data_file': (str(reader), 'rb'),
        'meta_file': (str(meta), 'rb'),
        'solver_profile_file': (str(solver), 'rb')
    }
    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(50)

    id = (res.json()['id'])
    response = requests.get(os.getenv('urlget') + f'task/{id}/result')
    response_to_shifts(response)
    shifts = response_to_shifts(response)

    expected_time = 198
    actual_time = len(list(shifts)) * 3
    assert int(actual_time) == int(expected_time)


