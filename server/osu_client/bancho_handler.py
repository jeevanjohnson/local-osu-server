from fastapi.routing import APIRouter
from fastapi import Header, Depends

bancho_handling_router = APIRouter(prefix="/c")

def logged_in(osu_token: str | None) -> bool:
    if osu_token:
        return True

    return False


@bancho_handling_router.get('/')
async def handle_request(
    osu_token: str | None = Header(default=None)
):
    
    if not logged_in(osu_token):
        # TODO: Finish Login
        ...
    
    # TODO: Finish Everything Related To Send Packets to the Player