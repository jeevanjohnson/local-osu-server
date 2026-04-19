"""
Purpose/Domain/Concept:
- This file builds the server with all the necessary routes & events for the application.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from constants.network import LOS_PORT
from controllers.domains.assets import assets
from controllers.domains.avatar import avatar
from controllers.domains.beatmaps import beatmaps
from controllers.domains.cho import bancho
from controllers.domains.osu import osu


app = FastAPI()

app.include_router(assets)
app.include_router(beatmaps)
app.include_router(avatar)
app.include_router(osu)

for subdomain in ["/c4", "/c5", "/c6", "/ce", "/c"]:
    app.include_router(bancho, prefix=subdomain)


def los_process() -> None:
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=LOS_PORT,
    )
