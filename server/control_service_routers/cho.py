from email import header
import httpx
from typing import Optional
from fastapi import APIRouter
from fastapi import Header
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi.responses import RedirectResponse
from .common.url import build_url
from .common.https import get_async_client

router = APIRouter()

CONTROL_SERVICE_URL = "http://127.0.0.1:5000"


@router.get("/")
async def bancho(
    http_client: httpx.AsyncClient = Depends(get_async_client),
    osu_token: Optional[str] = Header(None),
):
    parameters = {}

    if osu_token is None:
        response = await http_client.get(f"{CONTROL_SERVICE_URL}/bancho/login")
        if response.status_code not in range(200, 300):
            raise HTTPException(status_code=404)

        data = response.json()
        # TODO: think about packet structure
        # TODO: build nessary packets
        return Response(
            content=None,  # this is were the builded packet repsonse would be
            headers={"cho-token": data["user_name"]},
        )
    else:
        parameters["username"] = osu_token
        return RedirectResponse(
            build_url(f"{CONTROL_SERVICE_URL}/bancho/queued_packets", parameters)
        )
