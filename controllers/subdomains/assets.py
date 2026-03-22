"""
Purpose/Domain/Concept:
- This file builds the routes related to assets.ppy.sh
"""

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

from adapters.app_logger import app_logger

assets = APIRouter(
    prefix="/assets",
)


@assets.get("/{full_path:path}")
@app_logger.log(msg="router assets all")
async def all(full_path: str):
    return RedirectResponse(
        url=f"https://assets.ppy.sh/{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )
