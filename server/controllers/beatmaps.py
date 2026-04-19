from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse


beatmaps = APIRouter(
    prefix="/b",
)


@beatmaps.get("/{full_path:path}")
async def all(full_path: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"https://b.ppy.sh/{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )