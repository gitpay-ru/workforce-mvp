import requests
import json
import time
import os
from dotenv import load_dotenv, find_dotenv


def test_calculation_and_cancellation_of_the_launch():
    load_dotenv(find_dotenv())

    files = {
        "data_file": open('test_calculation_and_cancellation_of_the_launch/_data_file_improvisation.csv', 'rb'),
        "meta_file": open('test_calculation_and_cancellation_of_the_launch/_meta_file_calculation_and_cancellation_of_the_launch.json', 'rb'),
        "solver_profile_file": open('test_calculation_and_cancellation_of_the_launch/_solver_profile_file.json', 'rb')
    }
    with open(f'test_calculation_and_cancellation_of_the_launch/_meta_file_calculation_and_cancellation_of_the_launch.json', 'r',
              encoding='utf-8') as f:
        meta = json.load(f)

    res = requests.post(os.getenv('urlpost'), files=files)
    time.sleep(50)
    print(res.status_code)

    id = (res.json()['id'])
    response = requests.get(os.getenv('urlget') + f'task/{id}/cancel')
    assert response.status_code == 200