import pytest
import requests
import json
import csv
import time
from datetime import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

with open(f'.//_data_file_imp.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)

with open(f'.//_meta_file.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)

with open(f'.//_solver_profile_file.json', 'r', encoding='utf-8') as f:
    solver = json.load(f)


files = {
    "data_file": open('_data_file_imp.csv', 'rb'),
    "meta_file": open('_meta_file.json', 'rb'),
    "solver_profile_file": open('_solver_profile_file.json', 'rb')
}

res = requests.post(os.getenv('urlpost'), files=files)
print(res.json()['id'])
time.sleep(8)

id = (res.json()['id'])
response = requests.get(os.getenv('urlget'))


shifts_duration = {}
for s in meta['shifts']:
    shifts_duration[s['id']] = timedelta(minutes= int(s['duration'][:-3]) * 60+ int(s['duration'][-2:]))

print(shifts_duration)


format = '%d.%m.%y %H:%M'
shifts = map(
        lambda x: dict(Employee = str(x['employeeId']),
                       StartDateTime = datetime.strptime(f"{x['shiftDate']} {x['shiftTimeStart']}", format),
                       FinishDateTeme = datetime.strptime(f"{x['shiftDate']} {x['shiftTimeStart']}", format) + shifts_duration[x['shiftId']],
                       Shift = x['shiftId'])
        , response.json()["campainSchedule"]
)


expected_time = 9 * 22 # 198


actual_time = len(list(shifts)) * 9
print(actual_time)



def test_time_count():
    assert int(actual_time) == int(expected_time)


if __name__ == '__main__':
    pytest.main()