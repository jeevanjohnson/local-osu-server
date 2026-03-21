from fastapi import APIRouter, status
from fastapi.responses import FileResponse, JSONResponse

import usecases.resources

resources = APIRouter(
    prefix="/resources",
)


@resources.get("/{full_path:path}")
async def get_resource(full_path: str):
    resource = usecases.resources.retrive(full_path)

    if resource is None:
        return JSONResponse(
            content={"error": f"no file `./resources/{full_path}` found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return FileResponse(resource)
