from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from server.usecases.domain.player import PlayerDomainUseCase

avatar = APIRouter(
    prefix="/a",
)

PLAYER_DOMAIN_USECASE = PlayerDomainUseCase()


@avatar.get("/{user_id}")
async def get_avatar(
    user_id: int,
):
    if user_id != 2:
        avatar_url = f"https://a.ppy.sh/{user_id}"
    else:
        avatar_url = await PLAYER_DOMAIN_USECASE.retrive_current_user_avatar()

    return RedirectResponse(
        url=avatar_url,
        status_code=status.HTTP_301_MOVED_PERMANENTLY
    )
