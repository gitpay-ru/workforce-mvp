from celery.result import AsyncResult
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pathlib import Path
import pyworkforce as pw
from version import __version__

from worker import create_task, terminate_task

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get('/health')
def health():
    return JSONResponse(status_code=200)

@app.get('/version')
def version():
    result = {
        'pyworkforce': pw.__version__,
        'version': __version__
    }
    return JSONResponse(result)

def iterfile(path):
    with open(path, mode="rb") as file_like:
        yield from file_like

@app.post("/task", status_code=201)
def submit_task(
    data_file: UploadFile = File(...),
    meta_file: UploadFile = File(...),
    solver_profile_file: UploadFile = File(...)
):
    with open("./tmp/data", "wb") as f:
        f.write(data_file.file.read())

    with open("./tmp/meta", "wb") as f:
        f.write(meta_file.file.read())

    with open("./tmp/solver-profile", "wb") as f:
        f.write(solver_profile_file.file.read())

    task = create_task.delay()
    return JSONResponse({"id": task.id})


@app.get("/task/{id}/status")
def get_task_status(id):
    try:
        task_result = AsyncResult(id)
        result = {
            "id": id,
            "status": task_result.status
        }
        return JSONResponse(result)
    except:
        return JSONResponse(status_code=404)


@app.get("/task/{id}/result")
def get_schedule_result(id):
    fpath = f'./tmp/{id}/rostering.json'
    if Path(fpath).exists():
        return StreamingResponse(iterfile(fpath), media_type = "application/octet-stream")
    else:
        return JSONResponse(status_code=404)

@app.get("/task/{id}/statistics-results")
def get_stats_result(id):
    fpath = f'./tmp/{id}/statistics_output.json'
    if Path(fpath).exists():
        return StreamingResponse(iterfile(fpath), media_type="application/octet-stream")
    else:
        return JSONResponse(status_code=404)

@app.get("/task/{id}/cancel")
def cancel_task(id):
    try:
        res = terminate_task.delay(id)
        return JSONResponse({"id": res.id})
    except:
        return JSONResponse(status_code=404)