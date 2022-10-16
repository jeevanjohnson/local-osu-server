import uvicorn
from fastapi import FastAPI

from routers import web_router
from routers import cho_router
from routers import ava_router
from routers import maps_router


def init_app() -> FastAPI:
    app = FastAPI()

    app.include_router(web_router, prefix="/osu")

    for path in ("/c4", "/c5", "/c6", "/ce", "/c"):
        app.include_router(cho_router, prefix=path)

    app.include_router(ava_router, prefix="/a")

    app.include_router(maps_router, prefix="/b")

    return app


app = init_app()


def main() -> int:
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
