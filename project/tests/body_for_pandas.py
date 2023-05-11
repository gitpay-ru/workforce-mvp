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

employeeId = df['employeeId']
shiftId = df['shiftId'][0]
shiftTimeStart = df['shiftTimeStart'][0]


scheduleTimeStart = meta['shifts'][0]['scheduleTimeStart']
scheduleTimeEndStart = meta['shifts'][0]['scheduleTimeEndStart']
id = meta['shifts'][0]['id']