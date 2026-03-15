"""
Purpose/Domain/Concept:
- This file builds the routes related to assets.ppy.sh
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
import usecases.assets

assets = APIRouter(
    prefix="/assets",
)

@assets.get("/menu-content.json")
async def get_menu_content():
    return JSONResponse(
        content=usecases.assets.menu_content_response(),
        status_code=200
    )