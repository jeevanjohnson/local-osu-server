import uvicorn
from fastapi import FastAPI

import core.usecases.domain.port as port_usecases
from server.controllers.assets import assets
from server.controllers.avatar import avatar
from server.controllers.beatmaps import beatmaps
from controllers.domains.cho import bancho
from controllers.domains.osu import osu

def start() -> None:
    app = FastAPI()

    app.include_router(assets)
    app.include_router(beatmaps)
    app.include_router(avatar)
    app.include_router(osu)

    for subdomain in ["/c4", "/c5", "/c6", "/ce", "/c"]:
        app.include_router(bancho, prefix=subdomain)

    port = port_usecases.assign_port_to("server")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
    )

def stop() -> None:
    port_usecases.clear_port_for("server")