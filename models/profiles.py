from typing import Optional
from sqlmodel import SQLModel
from sqlmodel import Field


class Profile(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    avatar_url: Optional[str] = Field(default=None)
