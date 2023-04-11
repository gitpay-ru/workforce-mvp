from celery.result import AsyncResult
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from typing import Any, Callable, Set, TypeVar
from fastapi.openapi.utils import generate_operation_id
from fastapi.routing import APIRoute
from pathlib import Path
import pyworkforce as pw
from version import __version__

from worker import create_task, terminate_task

app = FastAPI()

F = TypeVar("F", bound=Callable[..., Any])

def remove_422(func: F) -> F:
    func.__remove_422__ = True
    return func

def remove_422s(app: FastAPI) -> None:
    openapi_schema = app.openapi()
    operation_ids_to_update: Set[str] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = route.methods or ["GET"]
        if getattr(route.endpoint, "__remove_422__", None):
            for method in methods:
                operation_ids_to_update.add(generate_operation_id(route=route, method=method))
    paths = openapi_schema["paths"]
    for path, operations in paths.items():
        for method, metadata in operations.items():
            operation_id = metadata.get("operationId")
            if operation_id in operation_ids_to_update:
                metadata["responses"].pop("422", None)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get('/health', responses={
    200: {
        "content": {
            "application/json": {
                "example": {}
            }},
        "description": "Return health check"
    }
})
def health():
    return JSONResponse({}, status_code=200)

@app.get('/version', responses={
    200: {
        "content": {
            "application/json": {
                "example": {"pyworkforce": "0.7.1", "version": "1.1.1"}
            }},
        "description": "Return version of pyworkforce and api"
    }
})
def version():
    result = {
        'pyworkforce': pw.__version__,
        'version': __version__
    }
    return JSONResponse(result)

def iterfile(path):
    with open(path, mode="rb") as file_like:
        yield from file_like

@app.post("/task", status_code=201, responses={
    201: {
        "content": {
            "application/json": {
                "example": {"id": "08234f72-29c9-4527-861c-b3d29aabf0e4"}
            }},
        "description": "Return task id"
    },
    422: {
            "content": {
            "application/json": {
                "example": {"detail":[{"loc":["body","solver_profile_file"],"msg":"field required","type":"value_error.missing"}]}
            }},
        "description": "Validates input files"
    }
})

def submit_task(
    data_file: UploadFile = File(..., description="Comma separated csv file with columns: tc,call_volume,aht,service_level,art"),
    meta_file: UploadFile = File(..., description="Json meta file that contains: activities, shifts, schemas and eployees"),
    solver_profile_file: UploadFile = File(..., description="Execution parameters for: scheduling, rostering, breaks")
):
    with open("./tmp/data", "wb") as f:
        f.write(data_file.file.read())

    with open("./tmp/meta", "wb") as f:
        f.write(meta_file.file.read())

    with open("./tmp/solver-profile", "wb") as f:
        f.write(solver_profile_file.file.read())

    task = create_task.delay()
    return JSONResponse({"id": task.id}, status_code=201)

@app.get("/task/{id}/status", responses={
    200: {
        "content": {
            "application/json": {
                "example": {
                    "id": "cc6b3345-4207-4ebc-94a2-0c8f03d08bb3",
                    "status": "FAILURE"
                    }
            }},
        "description": "Return task id and current status"
    },
    404: {
        "description": "Task with provided id not found"
    }
})
@remove_422
def get_task_status(id):
    try:
        task_result = AsyncResult(id)

        if(task_result.status == 'PENDING'):
            return JSONResponse(status_code=404)

        result = {
            "id": id,
            "status": task_result.status
        }
        return JSONResponse(result)
    except:
        return JSONResponse(status_code=404)


@app.get("/task/{id}/result", responses={
    200: {
        "description": "Return json file with results"
    },
    404: {
        "description": "Task with provided id not found"
    }
})
@remove_422
def get_schedule_result(id):
    fpath = f'./tmp/{id}/rostering.json'
    if Path(fpath).exists():
        return StreamingResponse(iterfile(fpath), media_type = "application/octet-stream")
    else:
        return JSONResponse(status_code=404)

@app.get("/task/{id}/statistics-results", responses={
    200: {
        "description": "Return json file with statistics"
    },
    404: {
        "description": "Task with provided id not found"
    }
})
@remove_422
def get_stats_result(id):
    fpath = f'./tmp/{id}/statistics_output.json'
    if Path(fpath).exists():
        return StreamingResponse(iterfile(fpath), media_type="application/octet-stream")
    else:
        return JSONResponse(status_code=404)

@app.get("/task/{id}/cancel", responses={
    200: {
         "content": {
            "application/json": {
                "example": {
                    "id": "cc6b3345-4207-4ebc-94a2-0c8f03d08bb3"
                    }
            }},
        "description": "Cancel task submited"
    },
    404: {
        "description": "Task with provided id not found"
    }
})
@remove_422
def cancel_task(id):
    try:
        task_result = AsyncResult(id)
        if(task_result.status == 'PENDING'):
            return JSONResponse(status_code=404)

        res = terminate_task.delay(id)
        return JSONResponse({"id": res.id})
    except:
        return JSONResponse(status_code=404)

remove_422s(app)
