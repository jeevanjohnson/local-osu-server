from fastapi import FastAPI
import uvicorn
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.logger import logger
import settings
# import pipreqs



# TODO: Use Relic for data
# The idea is to allow the user to either accept/reject the offer to send data to relic
# so that I have some more data that I can use if their is a bug or something
# labels: enhancement

# TODO: Find an alternative to Jira x Github integration for "TODO's"
# labels: enhancement

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DEVELOPER:
        logger.info("Running on Developer Mode")

    # Each component is responsible for a different part of the server and SOLEY that part
    # This is to make sure that the server is modular and easy to maintain
    # If a component is making multiple responsibilities, then it should be split into multiple components 👍
    import frontend # Responsible for being the "GUI" for the user
    import osu_client # Responsible for capturing and processing requests from the osu! client and redirecting them to the according components
                      # Also responsible for managing the osu! client
    import api # Responsible for retriving and processing information for the sake of manging the sqlite db of the server
    import local_data_fetcher # Responsible for fetching local data from the user's computer

    app.include_router(frontend.web_client_router)
    app.include_router(osu_client.bancho_handling_router)
    app.include_router(osu_client.application_router)
    app.include_router(api.api_authentication_router)
    app.include_router(api.api_configuration_router)
    app.include_router(local_data_fetcher.api_local_data_fetching_router)

    # static is the default folder that fastapi uses for grabbing
    # javascript and css files

    web_path_for_css_and_javascript_files = '/static'
    app.mount(
        web_path_for_css_and_javascript_files,
        StaticFiles(directory='./server/frontend/static'),
        name='static'
    )

    # TODO: Add an easier method of connecting without mitmproxy
    # preferably the "cloudflare method"

    yield


app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "FastAPI server is running!"}


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
