from fastapi import APIRouter, Response
from constants import SEASONAL_BG_GIT_URL
import json

osu = APIRouter(
    prefix="/osu",
)

# osu is weird for this
@osu.get("/web/osu-getseasonal.php")
async def get_seasonal_backgrounds():
    return Response(
        content=json.dumps([SEASONAL_BG_GIT_URL])
    )