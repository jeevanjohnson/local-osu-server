from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="./server/frontend/pages")

web_client_router = APIRouter()

@web_client_router.get("/onboarding")
async def first_launch(
    request: Request
):
    # your osu!.exe path
    # do you want pp leaderboards
    # do you want to rank your scores based on pp or score
    # how many scores do you want to see on the leaderboad (max 100)
    # do you want to have the ability to modify maps through the fun orange applciation and gain pp from it
    # osu api key (might can abandon)
    # osu daily api key
    # osu api v2
    
    return templates.TemplateResponse(
        name="onboarding.html", 
        context={"request": request},
    )
    
# TODO: Setup an `open/close osu` button on the home page
# Basically run `osu!.exe -devserver localosuserver.com` in the background