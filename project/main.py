from celery.result import AsyncResult
from fastapi import Body, FastAPI, File, UploadFile, Form
from typing import List
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from celery import current_task
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse
import json
from typing import Union
from pydantic import BaseModel

from worker import create_schedule, create_roster

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# @app.get("/")
# def home(request: Request):
#     return templates.TemplateResponse("home.html", context={"request": request})

@app.post("/scheduling", status_code=201)
def submit_schedule_coverage_task(
    shift_names: str = Form("Morning_12_5_11_15,Night_12_17_21_15"),
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
    resources: list = []
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
                "num_days": 7,
                "resources": ["e.johnston@randatmail.com","d.harper@randatmail.com","m.hawkins@randatmail.com","m.ellis@randatmail.com",
    "b.campbell@randatmail.com","s.richards@randatmail.com","d.taylor@randatmail.com","h.myers@randatmail.com",
    "j.evans@randatmail.com","s.brooks@randatmail.com","a.montgomery@randatmail.com",
    "c.hunt@randatmail.com","v.owens@randatmail.com","a.brown@randatmail.com",
    "r.armstrong@randatmail.com","m.murray@randatmail.com","b.evans@randatmail.com",
    "m.brown@randatmail.com","s.thompson@randatmail.com","a.ryan@randatmail.com",
    "r.carter@randatmail.com","j.payne@randatmail.com","s.perkins@randatmail.com",
    "t.west@randatmail.com","d.stevens@randatmail.com","l.gibson@randatmail.com",
    "m.crawford@randatmail.com","a.barnes@randatmail.com","m.howard@randatmail.com",
    "t.chapman@randatmail.com","s.harris@randatmail.com","a.farrell@randatmail.com",
    "d.douglas@randatmail.com","a.douglas@randatmail.com","j.cole@randatmail.com",
    "v.myers@randatmail.com","l.owens@randatmail.com","h.robinson@randatmail.com",
    "s.spencer@randatmail.com","v.brooks@randatmail.com","h.turner@randatmail.com",
    "e.elliott@randatmail.com","a.adams@randatmail.com","m.higgins@randatmail.com",
    "j.cole@randatmail.com","m.ryan@randatmail.com","l.wilson@randatmail.com",
    "j.higgins@randatmail.com","v.ryan@randatmail.com","c.perry@randatmail.com",
    "c.wright@randatmail.com","f.myers@randatmail.com","c.allen@randatmail.com",
    "c.stevens@randatmail.com","c.campbell@randatmail.com"],
                "shifts": ["Morning_8_5_6_60", "Afternoon_8_13_14_60", "Night_8_21_22_60", "Mixed_6_9_10_60"],
                "min_working_hours": 40,
                "max_resting": 1,
                "non_sequential_shifts": [{"origin":"Night_8_21_0", "destination":"Morning_8_5_0"}],
                "banned_shifts": [{"resource":"e.johnston@randatmail.com", "shift": "Night_8_21_0", "day":  0}],
                "required_resources": {"Morning_8_5_0": [9, 12, 8, 10, 13, 10, 14],
                        "Afternoon_8_13_0":  [11, 13, 10, 11, 9, 11, 7],
                        "Night_8_21_0":  [8, 7, 5, 15, 7, 8, 6],
                        "Mixed_6_9_0":  [2, 4, 18, 7, 10, 5, 17]},
                "resources_preferences": [{"resource":  "d.harper@randatmail.com", "shift": "Morning_8_5_0"}],
                "resources_prioritization":  [{"resource": "d.harper@randatmail.com", "weight": 0.8}]
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
   return StreamingResponse(iterfile(f'{id}_rostering.json'), media_type = "application/json")

@app.get("/rostering/{id}/image")
def get_rostering_image(id):
    return StreamingResponse(iterfile(f'{id}_image.png'), media_type = "image/png")
    