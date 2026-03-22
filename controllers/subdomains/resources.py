from fastapi import APIRouter, status
from fastapi.responses import FileResponse, JSONResponse

import usecases.resources
from adapters.app_logger import app_logger

resources = APIRouter(
    prefix="/resources",
)


@resources.get("/{full_path:path}")
@app_logger.log(msg="router resources get")
async def get_resource(full_path: str):
    resource = usecases.resources.retrive(full_path)

    if resource is None:
        return JSONResponse(
            content={"error": f"no file `./resources/{full_path}` found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return FileResponse(resource)
