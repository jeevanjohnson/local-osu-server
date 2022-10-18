from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter()  # Path: /


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        context={
            "request": request,
        },
    )
