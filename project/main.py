from celery.result import AsyncResult
from fastapi import Body, FastAPI, File, UploadFile
from typing import List, Optional, Union
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from celery import current_task
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from pathlib import Path

from worker import create_task

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def task_exists(id):
    t = Path(f'./tmp/{id}')
    return t.exists()

def iterfile(path):
    with open(path, mode="rb") as file_like:
        yield from file_like

@app.post("/task", status_code=201)
def submit_task(
    data_file: UploadFile = File(...),
    meta_file: UploadFile = File(...)
):
    with open("./tmp/data", "wb") as f:
        f.write(data_file.file.read())

    with open("./tmp/meta", "wb") as f:
        f.write(meta_file.file.read())

    task = create_task.delay()
    return JSONResponse({"id": task.id})


@app.get("/task/{id}/status")
def get_task_status(id):

    if not task_exists(id):
        return JSONResponse(status_code=404)

    task_result = AsyncResult(id)
    result = {
        "id": id,
        "status": task_result.status,
        "result": task_result.result
    }
    return JSONResponse(result)


@app.get("/task/{id}/result")
def get_schedule_result(id):
    if not task_exists(id):
        return JSONResponse(status_code=404)

    return StreamingResponse(iterfile(f'./tmp/{id}/rostering.json'), media_type = "application/octet-stream")


@app.get("/task/{id}/statistics-results")
def get_stats_result(id):
    if not task_exists(id):
        return JSONResponse(status_code=404)
    return StreamingResponse(iterfile(f'./tmp/{id}/statistics_output.json'), media_type="application/octet-stream")

