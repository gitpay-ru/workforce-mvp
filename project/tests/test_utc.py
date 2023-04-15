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



def test_actual_time_v2():
    load_dotenv(find_dotenv())

    with open(f'./_data_file_imp.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

    with open(f'./_meta_file.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(f'./_solver_profile_file.json', 'r', encoding='utf-8') as f:
        solver = json.load(f)

    files = {
        "data_file": open('_data_file_imp.csv', 'rb'),
        "meta_file": open('_meta_file.json', 'rb'),
        "solver_profile_file": open('_solver_profile_file.json', 'rb')
    }

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(8)

    id = (res.json()['id'])
    op = f'task/{id}/result'
    sos = os.getenv('urlget')
    response = requests.get((sos) + str(op))


    response_dict = response.json()
    df = pd.DataFrame(response_dict)
    df['shiftId'] = df.apply(lambda t: t['campainSchedule']['shiftId'], axis=1)
    df['shiftTimeStart'] = df.apply(lambda t: t['campainSchedule']['shiftTimeStart'], axis=1)
    print(df['shiftId'], df['shiftTimeStart'])



    print(meta['shifts'])
    print(meta['shifts'][0]['scheduleTimeStart'])
    print(meta['shifts'][0]['scheduleTimeEndStart'])

    for item in meta['shifts']:
        print(item['scheduleTimeStart'])


