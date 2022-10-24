from fastapi import HTTPException
from typing import Optional
import settings
from fastapi import APIRouter
from fastapi import Request
import usecases
from fastapi.responses import RedirectResponse
from fastapi import Depends
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter()  # Path: /


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        context={
            "request": request,
            "settings": settings,
        },
    )


async def get_profile_name(request: Request) -> Optional[str]:
    if request.method == "GET":
        return None

    return usecases.request.get_profile_name_from_args(
        usecases.request.parse_body_args(
            await request.body(),
        ),
    )


@router.get("/create")
@router.post("/create")
async def create(
    request: Request,
    profile_name: Optional[str] = Depends(get_profile_name),
):
    if request.method == "GET":
        return templates.TemplateResponse(
            name="create.html",
            context={
                "request": request,
                "settings": settings,
            },
        )
    elif request.method == "POST":
        if profile_name is None:
            raise HTTPException(status_code=404, detail="profile name is none?")

        profile_exist = usecases.profiles.exist(profile_name)
        if profile_exist:
            raise HTTPException(status_code=409, detail="profile name already exist")

        profile_id = usecases.profiles.create(profile_name)

        return RedirectResponse(
            url=f"{settings.BASE_URL}/profile/{profile_name}",
        )
    else:
        raise HTTPException(
            status_code=404,
            detail="request method is not allowed",
        )


@router.get("/login")
async def login(
    request: Request,
):
    profiles = usecases.profiles.all()

    return templates.TemplateResponse(
        name="login.html",
        context={
            "request": request,
            "settings": settings,
            "profiles": profiles,
        },
    )


@router.get("/login/{profile_name}")
async def profile(
    request: Request,
    profile_name: str,
):
    profile = usecases.profiles.from_name(profile_name)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="profile not found",
        )

    return templates.TemplateResponse(
        name="profile.html",
        context={
            "request": request,
            "settings": settings,
            "profile": profile,
        },
    )
