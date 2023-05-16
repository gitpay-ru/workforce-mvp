import pytest
import requests
import json
import csv
import time
import os
from dotenv import load_dotenv, find_dotenv
import pandas as pd

with open(f'test_first_employees_shift_time_start/_data_file_improvisation.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)

with open(f'test_first_employees_shift_time_start/_meta_file_first_employees_shift_time_start.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)

with open(f'test_first_employees_shift_time_start/_solver_profile_file.json', 'r', encoding='utf-8') as f:
    solver = json.load(f)



def test_first_employees_shift_time_start():
    load_dotenv(find_dotenv())

    files = {
        "data_file": open('test_first_employees_shift_time_start/_data_file_improvisation.csv', 'rb'),
        "meta_file": open('test_first_employees_shift_time_start/_meta_file_first_employees_shift_time_start.json', 'rb'),
        "solver_profile_file": open('test_first_employees_shift_time_start/_solver_profile_file.json', 'rb')
    }
    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(20)

    id = (res.json()['id'])
    response = requests.get(os.getenv('urlget') + f'task/{id}/result')

    response_dict = response.json()
    df = pd.DataFrame(response_dict)
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

