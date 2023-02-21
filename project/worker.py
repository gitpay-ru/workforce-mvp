import os
import shutil
import json

import pandas as pd
from pathlib import Path

from celery import Celery
from celery import current_task

from pyworkforce.staffing import MultiZonePlanner

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

@celery.task(name="create_task")
def create_task():

    output_dir = f'./tmp/{current_task.request.id}'
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    shutil.copyfile("./tmp/data", f'./tmp/{current_task.request.id}/input')
    shutil.copyfile("./tmp/meta", f'./tmp/{current_task.request.id}/meta')

    input_csv_path = f'./tmp/{current_task.request.id}/input'
    input_meta_path = f'./tmp/{current_task.request.id}/meta'
    solver_profile_path = f'./tmp/{current_task.request.id}/profile'

    df = pd.read_csv(input_csv_path, parse_dates=[0], index_col=0)
    with open(input_meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    with open(solver_profile_path, 'r', encoding='utf-8') as f:
        profile = json.load(f)

    mzp = MultiZonePlanner(df, meta, profile, output_dir)
    mzp.solve()

    return True

@celery.task(name="terminate_task")
def terminate_task(task_id):
    celery.control.revoke(task_id, terminate=True)
