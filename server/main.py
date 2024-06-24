from fastapi import FastAPI
import uvicorn
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.logger import logger
# import settings
# import pipreqs

# TODO: Use Relic for data
# The idea is to allow the user to either accept/reject the offer to send data to relic
# so that I have some more data that I can use if their is a bug or something
# labels: enhancement

# TODO: Find an alternative to Jira x Github integration for "TODO's"
# labels: enhancement

@asynccontextmanager
async def lifespan(app: FastAPI):
    # if settings.DEVELOPER:
    #     logger.info("Running on Developer Mode")

    # add all necessary routerefs
    import frontend
    import osu_client
    import api

    app.include_router(frontend.web_client_router)
    app.include_router(osu_client.bancho_handling_router)
    app.include_router(api.api_authentication_router)

    # static is the default folder that fastapi uses for grabbing
    # javascript and css files

    # web_path_for_css_and_javascript_files = '/static'
    # app.mount(
    #     web_path_for_css_and_javascript_files,
    #     StaticFiles(directory='./server/frontend/static'),
    #     name='static'
    # )

    # TODO: Add an easier method of connecting without mitmproxy
    # preferably the "cloudflare method"

    yield


app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "FastAPI server is running!"}

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
