"""
Purpose/Domain/Concept:
- This file builds the routes related to b.ppy.sh
"""

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

from adapters import log_time

beatmaps = APIRouter(
    prefix="/b",
)


@beatmaps.get("/{full_path:path}")
@log_time
async def all(full_path: str):
    return RedirectResponse(
        url=f"https://b.ppy.sh/{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )
