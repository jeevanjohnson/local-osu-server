import uvicorn
from jays_tools.services import ReadinessSignal, Service
from fastapi import FastAPI

# from server.controllers.assets import assets
# from server.controllers.avatar import avatar
# from server.controllers.beatmaps import beatmaps
# from server.controllers.cho import bancho
# from server.controllers.osu import osu
from contextlib import asynccontextmanager
from constants import Ports


def start(readiness_signal: ReadinessSignal) -> None:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        readiness_signal.set()
        yield

    app = FastAPI(lifespan=lifespan)

    # app.include_router(assets)
    # app.include_router(beatmaps)
    # app.include_router(avatar)
    # app.include_router(osu)

    # for subdomain in ["/c4", "/c5", "/c6", "/ce", "/c"]:
    #     app.include_router(bancho, prefix=subdomain)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=Ports.SERVER,
    )


def ServerService() -> Service:
    return Service(
        name="Server Service",
        description="Handles all osu! client interactions.",
        start_func=start,
    )
