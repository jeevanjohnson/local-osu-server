from typing import Optional
from fastapi import APIRouter
from fastapi import Header
from fastapi.responses import RedirectResponse

router = APIRouter()

BANCHO_SERVICE = "http://127.0.0.1:5001"


@router.get("/")
async def bancho(osu_token: Optional[str] = Header(None)):
    if not osu_token:
        return RedirectResponse(url=f"{BANCHO_SERVICE}/login")

    return RedirectResponse(url=f"{BANCHO_SERVICE}/queued_packets")
