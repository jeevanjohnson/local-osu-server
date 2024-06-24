import psutil
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

application_router = APIRouter(prefix="/application")

def kill_client() -> None:
    for process in psutil.process_iter():
        if process.name() == "osu!.exe":
            process.kill()

# TODO: the process of killing the process should probably be separated into a different file
@application_router.post("/kill")
async def kill_osu_client():
    try: 
        kill_client()
        return JSONResponse(content={"message": "osu! client killed"}, status_code=200)
    except:
        return JSONResponse(content={"message": "osu! client not found"}, status_code=404)