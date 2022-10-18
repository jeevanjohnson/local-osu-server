import os
import uvicorn
from fastapi import FastAPI
import globals
import httpx
import routers
import asyncio
from fastapi.staticfiles import StaticFiles
from daemons.score_submission import score_submission


def init_background_tasks(app: FastAPI) -> FastAPI:
    loop = asyncio.get_event_loop()
    loop.create_task(score_submission())

    print("Initialized background tasks & daemons")

    return app


def init_events(app: FastAPI):
    @app.on_event("startup")
    async def startup() -> None:
        globals.http.client = httpx.AsyncClient()

    print("Initialized events")

    return app


def init_routers(app: FastAPI) -> FastAPI:
    for path in ("/c4", "/c5", "/c6", "/ce", "/c"):
        app.include_router(routers.bancho_router, prefix=path)

    app.include_router(routers.avatar_router)
    app.include_router(routers.frontend_router)
    app.include_router(routers.osu_web_router)
    app.include_router(routers.beatmaps_router)

    print("Initialized routers")

    return app


def init_app() -> FastAPI:
    app = FastAPI()

    os.system("cls||clear")

    app = init_routers(app)
    app = init_events(app)
    app = init_background_tasks(app)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    return app


app = init_app()


def main() -> None:
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)


if __name__ == "__main__":
    raise SystemExit(main())
