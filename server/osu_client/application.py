import psutil
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
import settings
import os
from pathlib import Path
from constants import DEVSERVER_DOMAIN

application_router = APIRouter(prefix="/application")

def kill_client() -> None:
    for process in psutil.process_iter():
        if process.name() == "osu!.exe":
            process.kill()

def launch_client() -> None:
    if not settings.OSU_PATH:
        raise Exception("osu! path not found")
    
    osu_client_path = Path(settings.OSU_PATH) / "osu!.exe"
    
    os.startfile(str(osu_client_path), arguments=f"-devserver {DEVSERVER_DOMAIN}")

# TODO: the process of killing the process should probably be separated into a different file
@application_router.post("/kill")
async def kill_osu_client():
    try: 
        kill_client()
        return JSONResponse(content={"message": "osu! client killed"}, status_code=200)
    except:
        return JSONResponse(content={"message": "osu! client not found"}, status_code=404)
    
@application_router.post("/launch")
async def launch_osu_client():
    #try: 
        launch_client()
        return JSONResponse(content={"message": "osu! client launched"}, status_code=200)
    #except Exception as e:
        #return JSONResponse(content={"message": str(e)}, status_code=404)