from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse
from fastapi import Depends

import core.usecases.application.avatar as avatar_usecases
import server.dependencies as dependencies

avatar = APIRouter(
    prefix="/a",
)

@avatar.get("/{user_id}")
async def get_avatar(
    user_identifier: int | str = Depends(dependencies.user_identifier),
):
    avatar_url = avatar_usecases.get(user_identifier)

    return RedirectResponse(
        url=avatar_url, 
        status_code=status.HTTP_301_MOVED_PERMANENTLY
    )