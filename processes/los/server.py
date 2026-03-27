"""
Purpose/Domain/Concept:
- This file builds the server with all the necessary routes & events for the application.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from constants.network import LOS_PORT
from constants.paths import DATA
from controllers.domains.assets import assets
from controllers.domains.avatar import avatar
from controllers.domains.beatmaps import beatmaps
from controllers.domains.cho import bancho
from controllers.domains.osu import osu


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    paths: list[Path] = [DATA]
    for path in paths:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

    yield
    # Shutdown


app = FastAPI(lifespan=lifespan)


# @app.exception_handler(ClientResponseException)
# async def client_response_exception_handler(
#     _request: Request,
#     exc: ClientResponseException,
# ) -> Response:
#     return Response(content=exc.content, status_code=exc.status_code)


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
