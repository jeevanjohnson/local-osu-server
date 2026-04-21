from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse
from fastapi import Depends

import server.dependencies as dependencies
from core.usecases.domain.player import Player

avatar = APIRouter(
    prefix="/a",
)

@avatar.get("/{user_id}")
async def get_avatar(
    user_id: int,
    player: Player | None = Depends(dependencies.player)
):
    
    if user_id != 2:
        avatar_url = f"https://a.ppy.sh/{user_id}"
    elif player is None:
        avatar_url = "https://a.ppy.sh/"
    else:
        profile = player.get_profile()
        avatar_url = profile.avatar_url

    return RedirectResponse(
        url=avatar_url, 
        status_code=status.HTTP_301_MOVED_PERMANENTLY
    )