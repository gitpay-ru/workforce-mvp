import pytest
import requests
import json
import csv
import time
import pandas as pd



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

res = requests.post(f'http://31.133.120.7:8004/task', files=files)
print(res.json()['id'])
time.sleep(8)

id = (res.json()['id'])
response = requests.get(f'http://31.133.120.7:8004/task/{id}/result')


df = pd.read_json(
    'application_octet-stream_result_blob_http___31.133.120.7_8004_2c3abe0d-72a2-4b01-929c-c558d2b71b5d')
df['employeeId'] = df.apply(lambda t: t['campainSchedule']['employeeId'], axis=1)
print(df, df.describe())


expected_time = 198
actual_time = (df['employeeId'].count()*9)

def test_actual_time():
    assert int(actual_time) == int(expected_time)


if __name__ == '__main__':
    pytest.main()