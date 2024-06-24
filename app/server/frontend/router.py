from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="./server/frontend/pages")

web_client_router = APIRouter()

@web_client_router.get("/onboarding")
async def first_launch(
    request: Request
):
    # your osu!.exe path (ask filedialog for it)
    # do you want pp leaderboards (bool)
    # do you want to rank your scores based on pp or score (bool)
    # how many scores do you want to see on the leaderboad (max 100) (int)
    # do you want to have the ability to modify maps through the fun orange applciation and gain pp from it (bool)
    # osu api key (might can abandon) (str)
    # osu daily api key (str)
    # osu api v2 key (str)
    # osu username (str)
    # osu password (str)
    
    return templates.TemplateResponse(
        name="onboarding.html", 
        context={"request": request},
    )

@web_client_router.get("/dashboard")
async def dashboard(
    request: Request
):
    return templates.TemplateResponse(
        name="dashboard.html", 
        context={"request": request},
    )