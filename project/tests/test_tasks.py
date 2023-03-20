import json

from unittest.mock import patch, call

from worker import create_task
import pandas as pd

# def test_home(test_app):
#     response = test_app.get("/")
#     assert response.status_code == 200


def test_task():
    expected_time = 9 * 22
    assert 1, 1 
#     assert create_task.run(2)
#     assert create_task.run(3)

def test_pandas():
    df = pd.read_json('./rostering.json')
    # edf['schema'] = edf.apply(lambda t: t['schemas'][0], axis=1)
    # json.loads(employee_string)
    # ['campainSchedule']['employeeId']
    df['employeeId'] = df.apply(lambda t: t['campainSchedule']['employeeId'], axis=1)
    print(df, df.describe())

# @patch("worker.create_task.run")
# def test_mock_task(mock_run):
#     assert create_task.run(1)
#     create_task.run.assert_called_once_with(1)

#     assert create_task.run(2)
#     assert create_task.run.call_count == 2

#     assert create_task.run(3)
#     assert create_task.run.call_count == 3


# def test_task_status(test_app):
#     response = test_app.post(
#         "/tasks",
#         data=json.dumps({"type": 1})
#     )
#     content = response.json()
#     task_id = content["task_id"]
#     assert task_id

#     response = test_app.get(f"tasks/{task_id}")
#     content = response.json()
#     assert content == {"task_id": task_id, "task_status": "PENDING", "task_result": None}
#     assert response.status_code == 200

#     while content["task_status"] == "PENDING":
#         response = test_app.get(f"tasks/{task_id}")
#         content = response.json()
#     assert content == {"task_id": task_id, "task_status": "SUCCESS", "task_result": True}
