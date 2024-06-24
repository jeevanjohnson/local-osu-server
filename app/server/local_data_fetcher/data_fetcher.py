import psutil
from fastapi.routing import APIRouter
from pathlib import Path
from fastapi import Depends, Response
from fastapi.responses import JSONResponse

api_local_data_fetching_router = APIRouter(prefix="/local_data_fetcher")

# TODO: the process of getting the path should probably be separated into a different file
def get_osu_path() -> Path | None:
    # read every process that is opened and check if the process is osu!
    for process in psutil.process_iter():
        if process.name() == "osu!.exe":
            osu_path = Path(process.cwd())
            
            return osu_path
    
    # if the process is not found, return None
    return None

@api_local_data_fetching_router.get("/osu_path")
async def get_osu_path_route(
    osu_path: Path | None = Depends(get_osu_path)
):
    if osu_path is None:
        return Response(status_code=404, content="osu! path not found")
    
    return JSONResponse(content={"osu_path": str(osu_path)})