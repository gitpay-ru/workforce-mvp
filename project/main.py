from celery.result import AsyncResult
from fastapi import Body, FastAPI, File, UploadFile, Form, Depends
from typing import List, Optional, Union
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from celery import current_task
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
import json
from pydantic import BaseModel

from worker import create_schedule, create_roster, create_task

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# @app.get("/")
# def home(request: Request):
#     return templates.TemplateResponse("home.html", context={"request": request})

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

@app.get("/task/{id}")
def get_task_status(id):
    task_result = AsyncResult(id)
    result = {
        "id": id,
        "status": task_result.status,
        "result": task_result.result
    }
    return JSONResponse(result)

@app.get("/task/{id}/result")
def get_schedule_result(id):
    # return StreamingResponse(iterfile(f'{id}_rostering.json'), media_type = "application/json")
    return StreamingResponse(iterfile(f'{id}_rostering.json'), media_type = "application/octet-stream")

# @app.get("/task/{id}/image")
# def get_rostering_image(id):
#     return StreamingResponse(iterfile(f'{id}_image.png'), media_type = "image/png")

@app.post("/scheduling", status_code=201)
def submit_schedule_coverage_task(
    shift_names: str = Form("Day_9_6_13_15,Night_9_21_22_15"),
    files: UploadFile = File(...)
):
    # print(shifts_spec)
    f = files
    with open("./tmp/data", "wb") as file_object:
        file_object.write(f.file.read())
    task = create_schedule.delay(shift_names)
    return JSONResponse({"id": task.id})

@app.get("/scheduling/{id}")
def get_schedule_status(id):
    task_result = AsyncResult(id)
    result = {
        "id": id,
        "status": task_result.status,
        "result": task_result.result
    }
    return JSONResponse(result)

def iterfile(id):
    with open(f"./tmp/{id}", mode="rb") as file_like:
        yield from file_like

@app.get("/scheduling/{id}/result")
def get_schedule_result(id):
    return StreamingResponse(iterfile(f'{id}_scheduling.json'), media_type = "application/json")

class RosteringItem(BaseModel):
    num_days: int
    num_resources: int
    shifts: list = []
    min_working_hours: int
    max_resting: int
    non_sequential_shifts: list = []
    banned_shifts: list = []
    required_resources: dict
    resources_preferences: list = []
    resources_prioritization: list = []
    class Config:
        schema_extra = {
            "example": {
                "num_days": 31,
                "num_resources": 375,
                "shifts": [
                    "Day_9_6_0", "Day_9_6_15", "Day_9_6_30", "Day_9_6_45", "Day_9_7_0", "Day_9_7_15", "Day_9_7_30", "Day_9_7_45", "Day_9_8_0", "Day_9_8_15", "Day_9_8_30", "Day_9_8_45", "Day_9_9_0", "Day_9_9_15", "Day_9_9_30", "Day_9_9_45", "Day_9_10_0", "Day_9_10_15", "Day_9_10_30", "Day_9_10_45", "Day_9_11_0", "Day_9_11_15", "Day_9_11_30", "Day_9_11_45", "Day_9_12_0", "Day_9_12_15", "Day_9_12_30", "Day_9_12_45", "Night_9_21_0", "Night_9_21_15", "Night_9_21_30", "Night_9_21_45"
                ],
                "min_working_hours": 176,
                "max_resting": 9,
                "non_sequential_shifts": [{"origin":"Day_9_6_0", "destination":"Night_9_21_0"}],
                "banned_shifts": [{"resource":"emp_1", "shift": "Night_9_21_30", "day":  0}],
                "required_resources": { "Day_9_10_0": [ 3, 0, 0, 1, 41, 0, 18, 0, 18, 0, 3, 40, 48, 4, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 49, 0, 37, 7, 37, 0 ], "Day_9_10_15": [ 0, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 6, 0, 0, 2, 3, 0, 0, 0, 0, 0, 0 ], "Day_9_10_30": [ 0, 6, 5, 0, 0, 0, 0, 0, 0, 4, 0, 0, 26, 0, 0, 0, 0, 0, 0, 16, 0, 0, 0, 0, 0, 0, 31, 0, 0, 0, 0 ], "Day_9_10_45": [ 0, 0, 0, 0, 0, 25, 0, 3, 0, 0, 0, 0, 0, 0, 3, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 14, 0 ], "Day_9_11_0": [ 3, 0, 0, 0, 6, 0, 0, 2, 0, 0, 0, 4, 0, 0, 2, 0, 0, 0, 4, 11, 13, 2, 7, 0, 1, 5, 0, 0, 0, 0, 0 ], "Day_9_11_15": [ 10, 8, 0, 0, 0, 0, 12, 11, 0, 0, 0, 0, 0, 13, 11, 7, 0, 0, 0, 0, 0, 11, 0, 0, 0, 0, 0, 0, 13, 6, 0 ], "Day_9_11_30": [ 11, 2, 0, 0, 0, 0, 2, 6, 9, 0, 0, 3, 0, 2, 7, 2, 0, 0, 0, 0, 3, 9, 3, 0, 0, 3, 0, 3, 9, 1, 0 ], "Day_9_11_45": [ 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0 ], "Day_9_12_0": [ 1, 5, 0, 2, 3, 2, 0, 0, 2, 0, 2, 2, 0, 0, 0, 4, 0, 0, 3, 0, 0, 0, 0, 0, 0, 2, 3, 0, 0, 1, 0 ], "Day_9_12_15": [ 0, 2, 1, 1, 13, 0, 2, 0, 5, 0, 1, 0, 0, 0, 1, 3, 0, 1, 16, 0, 2, 3, 2, 0, 0, 16, 0, 2, 1, 0, 0 ], "Day_9_12_30": [ 11, 1, 0, 0, 0, 12, 0, 10, 1, 0, 0, 18, 17, 0, 11, 0, 0, 0, 0, 16, 0, 9, 5, 0, 0, 0, 13, 0, 13, 5, 0 ], "Day_9_12_45": [ 4, 7, 3, 4, 4, 3, 15, 4, 7, 5, 4, 0, 0, 17, 3, 7, 4, 4, 5, 2, 16, 5, 8, 4, 5, 6, 4, 19, 5, 29, 0 ], "Day_9_6_0": [ 41, 22, 9, 4, 17, 62, 42, 32, 13, 11, 4, 18, 66, 44, 38, 11, 9, 6, 18, 68, 47, 34, 12, 10, 4, 21, 77, 50, 41, 0, 14 ], "Day_9_6_15": [ 0, 0, 1, 0, 22, 0, 0, 0, 0, 0, 2, 22, 0, 1, 0, 0, 1, 0, 23, 0, 0, 0, 7, 0, 1, 25, 0, 0, 0, 19, 0 ], "Day_9_6_30": [ 0, 20, 1, 2, 0, 0, 0, 0, 28, 1, 0, 0, 0, 0, 0, 30, 1, 0, 0, 0, 1, 0, 26, 2, 1, 0, 0, 0, 0, 12, 0 ], "Day_9_6_45": [ 37, 18, 1, 0, 0, 32, 3, 36, 18, 1, 0, 0, 31, 0, 32, 18, 0, 0, 12, 11, 0, 44, 19, 1, 0, 0, 13, 6, 4, 30, 6 ], "Day_9_7_0": [ 0, 45, 0, 2, 1, 21, 53, 0, 2, 1, 0, 0, 22, 56, 0, 17, 0, 2, 29, 44, 54, 0, 2, 1, 2, 2, 34, 42, 41, 67, 0 ], "Day_9_7_15": [ 4, 0, 1, 0, 0, 0, 0, 9, 14, 0, 0, 50, 0, 0, 9, 0, 3, 0, 12, 0, 0, 12, 17, 0, 0, 53, 0, 0, 24, 5, 3 ], "Day_9_7_30": [ 9, 39, 0, 0, 57, 0, 0, 6, 34, 0, 2, 10, 0, 13, 8, 33, 0, 0, 9, 0, 0, 0, 56, 1, 0, 0, 0, 5, 0, 0, 0 ], "Day_9_7_45": [ 0, 0, 2, 1, 0, 20, 28, 0, 18, 3, 1, 0, 67, 0, 41, 19, 1, 1, 0, 21, 0, 0, 0, 0, 2, 0, 40, 0, 50, 26, 2 ], "Day_9_8_0": [ 42, 0, 2, 0, 0, 0, 0, 40, 0, 0, 0, 20, 0, 0, 0, 0, 2, 1, 0, 0, 18, 41, 0, 2, 0, 12, 58, 39, 0, 0, 1 ], "Day_9_8_15": [ 15, 0, 1, 1, 0, 0, 0, 1, 11, 2, 0, 29, 0, 0, 0, 10, 2, 0, 0, 0, 0, 15, 12, 2, 0, 0, 0, 0, 17, 0, 5 ], "Day_9_8_30": [ 19, 14, 1, 0, 47, 44, 0, 53, 15, 0, 1, 54, 0, 30, 33, 16, 0, 0, 49, 39, 31, 18, 48, 0, 1, 105, 0, 0, 25, 17, 1 ], "Day_9_8_45": [ 11, 45, 0, 1, 52, 13, 74, 0, 0, 1, 1, 0, 39, 63, 10, 44, 1, 1, 56, 22, 63, 40, 16, 0, 0, 21, 39, 105, 12, 85, 3 ], "Day_9_9_0": [ 0, 20, 0, 2, 10, 25, 23, 25, 54, 1, 0, 24, 0, 22, 40, 20, 2, 1, 10, 22, 24, 13, 12, 3, 0, 12, 0, 30, 0, 1, 9 ], "Day_9_9_15": [ 41, 0, 4, 0, 0, 4, 32, 0, 10, 0, 0, 0, 48, 36, 0, 0, 1, 0, 0, 56, 6, 0, 10, 2, 3, 0, 13, 11, 50, 0, 3 ], "Day_9_9_30": [ 39, 63, 0, 1, 79, 89, 14, 0, 60, 0, 0, 69, 0, 19, 37, 61, 2, 2, 83, 0, 42, 38, 66, 1, 0, 96, 50, 50, 47, 105, 0 ], "Day_9_9_45": [ 46, 17, 0, 0, 0, 0, 12, 80, 0, 3, 0, 0, 0, 20, 44, 23, 3, 0, 44, 47, 25, 45, 27, 3, 0, 0, 57, 14, 55, 0, 0 ], "Night_9_21_0": [ 0, 4, 4, 3, 0, 0, 10, 0, 0, 4, 3, 0, 0, 10, 0, 4, 4, 3, 0, 0, 10, 0, 0, 4, 3, 0, 0, 12, 0, 0, 5 ], "Night_9_21_15": [ 0, 0, 0, 0, 0, 7, 0, 0, 4, 0, 0, 0, 9, 0, 0, 0, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 10, 0, 0, 0, 0 ], "Night_9_21_30": [ 9, 0, 0, 0, 9, 2, 0, 8, 0, 0, 0, 9, 0, 0, 8, 0, 0, 0, 9, 0, 0, 8, 4, 0, 0, 10, 0, 0, 10, 0, 0 ], "Night_9_21_45": [ 0, 4, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 1, 4, 0, 0, 0, 0, 0, 0, 13, 0 ] },
                "resources_preferences": [{"resource":  "emp_1", "shift": "Day_9_6_0"}],
                "resources_prioritization":  [{"resource": "emp_2", "weight": 0.8}]
            }
        }

@app.post("/rostering", status_code=201)
def submit_rostering_task(
    payload: RosteringItem
):
    task = create_roster.delay( jsonable_encoder(payload))
    return JSONResponse({"id": task.id})

@app.get("/rostering/{id}")
def get_rostering_status(id):
    task_result = AsyncResult(id)
    result = {
        "id": id,
        "status": task_result.status,
        "result": task_result.result
    }
    return JSONResponse(result)

@app.get("/rostering/{id}/result")
def get_rostering_result(id):
#    return StreamingResponse(iterfile(f'{id}_rostering.json'), media_type = "application/json")
    return StreamingResponse(iterfile(f'{id}_rostering.json'), media_type = "application/octet-stream")





