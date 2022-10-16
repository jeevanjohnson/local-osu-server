from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()


class LoginResponse(BaseModel):
    osu_token = str


@router.get("/login")
async def login():
    return {"user_name": "dasdas"}
