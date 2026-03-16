from fastapi import APIRouter
from fastapi.responses import JSONResponse
from constants import SEASONAL_BG_GIT_URL

osu = APIRouter(
    prefix="/osu",
)

@osu.get("/web/osu-getseasonal.php")
async def get_seasonal_backgrounds():
    return JSONResponse(
        content=[SEASONAL_BG_GIT_URL]
    )