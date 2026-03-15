"""
Purpose/Domain/Concept:
- This file builds the server with all the necessary routes & events for the application.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from controllers.osuRouters.assets import assets
from controllers.osuRouters.beatmaps import beatmaps
from controllers.osuRouters.bancho import bancho
from controllers.osuRouters.avatar import avatar
from constants import DATA_FOLDER
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    paths: list[Path] = [DATA_FOLDER]
    for path in paths:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

    # Startup
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)

app.include_router(assets)
app.include_router(beatmaps)
app.include_router(avatar)

for subdomain in [
    '/c4', '/c5', '/c6', '/ce', '/c'
]:
    app.include_router(bancho, prefix=subdomain)