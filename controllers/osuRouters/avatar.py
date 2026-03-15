"""
Purpose/Domain/Concept:
- This file builds the routes related to a.ppy.sh
"""

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
import usecases.avatar

avatar = APIRouter(
    prefix="/a",
)

@avatar.get("/{user_id}")
async def get_avatar(user_id: int):
    if user_id != 2:
        return RedirectResponse(
            url=f"https://a.ppy.sh/{user_id}",
            status_code=301,
        )

    avatar_value = usecases.avatar.get_session_avatar()
    
    if avatar_value is None:
        return RedirectResponse(
            url=f"https://a.ppy.sh/{user_id}",
            status_code=301,
        )

    if isinstance(avatar_value, Path):
        return FileResponse(
            path=avatar_value,
            media_type="image/png"
        )
    else:
        return RedirectResponse(
            url=avatar_value,
            status_code=301
        )