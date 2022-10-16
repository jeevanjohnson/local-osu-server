import os
import uvicorn
from fastapi import FastAPI
import control_service_routers
import bancho_service_router


def init_control_routers(app: FastAPI) -> FastAPI:
    app.include_router(control_service_routers.web.router, prefix="/osu")

    for path in ("/c4", "/c5", "/c6", "/ce", "/c"):
        app.include_router(control_service_routers.cho.router, prefix=path)

    app.include_router(control_service_routers.ava.router, prefix="/a")

    app.include_router(control_service_routers.maps.router, prefix="/b")

    return app


def init_bancho_router(app: FastAPI) -> FastAPI:
    app.include_router(bancho_service_router.router, prefix="/bancho")

    return app


def init_app() -> FastAPI:
    app = FastAPI()

    app = init_control_routers(app)
    app = init_bancho_router(app)

    return app


app = init_app()


def main() -> None:
    os.system("clear")  # TODO: check operating system
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)


if __name__ == "__main__":
    raise SystemExit(main())
