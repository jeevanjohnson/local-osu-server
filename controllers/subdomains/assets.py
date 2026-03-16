"""
Purpose/Domain/Concept:
- This file builds the routes related to assets.ppy.sh
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from fastapi import status

assets = APIRouter(
    prefix="/assets",
)

@assets.get("/{full_path:path}")
async def all(full_path: str):
    return RedirectResponse(
            url=f"https://assets.ppy.sh/{full_path}",
            status_code=status.HTTP_301_MOVED_PERMANENTLY
    )