"""
Purpose/Domain/Concept:
- This file builds the routes related to a.ppy.sh
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

import services.avatar
from adapters import log_time

avatar = APIRouter(
    prefix="/a",
)


@avatar.get("/{user_id}")
@log_time
async def get_avatar(user_id: int):
    avatar_service_response = await services.avatar.get(user_id)

    if isinstance(avatar_service_response, Path):
        return FileResponse(path=avatar_service_response, media_type="image/png")

    return RedirectResponse(url=avatar_service_response, status_code=301)
