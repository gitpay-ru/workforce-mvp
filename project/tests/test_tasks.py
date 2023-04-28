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

def test_time():
    load_dotenv(find_dotenv())

    with open(f'./_data_file_imp.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

    with open(f'./_meta_one_person_176h.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(f'./_solver_profile_file.json', 'r', encoding='utf-8') as f:
        solver = json.load(f)

    files = {
        "data_file": open('_data_file_imp.csv', 'rb'),
        "meta_file": open('_meta_one_person_176h.json', 'rb'),
        "solver_profile_file": open('_solver_profile_file.json', 'rb')
    }

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(8)

    id = (res.json()['id'])
    op = f'task/{id}/result'
    sos = os.getenv('urlget')
    response = requests.get((sos) + str(op))

    shifts_duration = {}
    for s in meta['shifts']:
        shifts_duration[s['id']] = timedelta(minutes=int(s['duration'][:-3]) * 60 + int(s['duration'][-2:]))

    format = '%d.%m.%y %H:%M'
    shifts = map(
        lambda x: dict(Employee=str(x['employeeId']),
                       StartDateTime=datetime.strptime(f"{x['shiftDate']} {x['shiftTimeStart']}", format),
                       FinishDateTeme=datetime.strptime(f"{x['shiftDate']} {x['shiftTimeStart']}", format) +
                                      shifts_duration[x['shiftId']],
                       Shift=x['shiftId'])
        , response.json()["campainSchedule"]
    )

    minWorkingHours = meta['employees'][0]['minWorkingHours']
    maxWorkingHours = meta['employees'][0]['maxWorkingHours']

    actual_time = len(list(shifts)) * 9 - 22

    assert actual_time <= maxWorkingHours
    assert actual_time >= minWorkingHours

    # with open('res.json', 'w') as f:
    #     json.dump(response.json(), f)

