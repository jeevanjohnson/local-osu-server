from typing import Iterator
import httpx
from sqlmodel import Session
from sqlalchemy.future import Engine

# from sqlmodel.engine.create import _FutureEngine # might need this


class http:
    client: httpx.AsyncClient


class database:
    engine: Engine
