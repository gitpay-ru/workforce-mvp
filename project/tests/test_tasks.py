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



def test_actual_time():
    load_dotenv(find_dotenv())

    with open(f'./_data_file_imp.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

    with open(f'./_meta_file_first.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(f'./_solver_profile_file.json', 'r', encoding='utf-8') as f:
        solver = json.load(f)

    files = {
        "data_file": open('_data_file_imp.csv', 'rb'),
        "meta_file": open('_meta_file_first.json', 'rb'),
        "solver_profile_file": open('_solver_profile_file.json', 'rb')
    }

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(20)

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

    expected_time = 9 * 22  # 198

    actual_time = len(list(shifts)) * 3

    assert int(actual_time) == int(expected_time)

def test_actual_time_v2():
    load_dotenv(find_dotenv())

    with open(f'./_data_file_imp.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

    with open(f'./_meta_file_first.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(f'./_solver_profile_file.json', 'r', encoding='utf-8') as f:
        solver = json.load(f)

    files = {
        "data_file": open('_data_file_imp.csv', 'rb'),
        "meta_file": open('_meta_file_first.json', 'rb'),
        "solver_profile_file": open('_solver_profile_file.json', 'rb')
    }

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(20)

    id = (res.json()['id'])
    op = f'task/{id}/result'
    sos = os.getenv('urlget')
    response = requests.get((sos) + str(op))


    response_dict = response.json()
    df = pd.DataFrame(response_dict)
    df['employeeId'] = df.apply(lambda t: t['campainSchedule']['employeeId'], axis=1)


    expected_time = 198
    actual_time = (df['employeeId'].count() * 3)

    assert int(actual_time) == int(expected_time)


def test_first_employees_working_hours():
    load_dotenv(find_dotenv())

    with open(f'./_data_file_imp.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

    with open(f'./_meta_file_exp.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(f'./_solver_profile_file.json', 'r', encoding='utf-8') as f:
        solver = json.load(f)

    files = {
        "data_file": open('_data_file_imp.csv', 'rb'),
        "meta_file": open('_meta_file_exp.json', 'rb'),
        "solver_profile_file": open('_solver_profile_file.json', 'rb')
    }

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(20)

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


def test_shift_time_start():
    load_dotenv(find_dotenv())

    with open(f'./_data_file_imp.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

    with open(f'./_meta_file_first.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(f'./_solver_profile_file.json', 'r', encoding='utf-8') as f:
        solver = json.load(f)

    files = {
        "data_file": open('_data_file_imp.csv', 'rb'),
        "meta_file": open('_meta_file_first.json', 'rb'),
        "solver_profile_file": open('_solver_profile_file.json', 'rb')
    }

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(20)

    id = (res.json()['id'])
    op = f'task/{id}/result'
    sos = os.getenv('urlget')
    response = requests.get((sos) + str(op))

    response_dict = response.json()
    df = pd.DataFrame(response_dict)
    df['employeeId'] = df.apply(lambda t: t['campainSchedule']['employeeId'], axis=1)
    df['shiftId'] = df.apply(lambda t: t['campainSchedule']['shiftId'], axis=1)
    df['shiftTimeStart'] = df.apply(lambda t: t['campainSchedule']['shiftTimeStart'], axis=1)

    shiftId = df['shiftId'][0]
    shiftTimeStart = df['shiftTimeStart'][0]


    scheduleTimeStart = meta['shifts'][0]['scheduleTimeStart']
    scheduleTimeEndStart = meta['shifts'][0]['scheduleTimeEndStart']
    id = meta['shifts'][0]['id']



    assert shiftId == id
    assert shiftTimeStart >= scheduleTimeStart
    assert shiftTimeStart <= scheduleTimeEndStart
