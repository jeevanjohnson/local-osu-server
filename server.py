"""
Purpose/Domain/Concept:
- This file builds the server with all the necessary routes & events for the application.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from controllers.subdomains.assets import assets
from controllers.subdomains.beatmaps import beatmaps
from controllers.subdomains.bancho import bancho
from controllers.subdomains.avatar import avatar
from controllers.subdomains.osu import osu
from controllers.subdomains.resources import resources
from constants import DATA_FOLDER
from pathlib import Path
import usecases.server_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    paths: list[Path] = [DATA_FOLDER]
    for path in paths:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
    
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)

app.include_router(assets)
app.include_router(beatmaps)
app.include_router(avatar)
app.include_router(osu)
app.include_router(resources)

for subdomain in [
    '/c4', '/c5', '/c6', '/ce', '/c'
]:
    app.include_router(bancho, prefix=subdomain)