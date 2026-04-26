import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from jays_tools.services import Service, ReadinessSignal
from constants import Ports
from nicegui import ui
from fastapi import FastAPI as BaseFastAPI
from contextlib import asynccontextmanager


class FastAPI(BaseFastAPI):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.readiness_signal: ReadinessSignal


@asynccontextmanager
async def lifespan(app: FastAPI):
    pages = Path(__file__).parent / "pages"
    for page in pages.glob("*.py"):
        module_name = page.stem
        page = __import__(
            f"interface.pages.{module_name}", fromlist=[module_name])
        try:
            page.build(template)
        except AttributeError:
            print(
                f"Page module {module_name} does not have a build function."
            )
            sys.exit(1)

    app.readiness_signal.set()
    webbrowser.open(f"http://localhost:{Ports.INTERFACE}/")
    yield

app = FastAPI(lifespan=lifespan)


def template() -> None:
    ui.add_head_html(""" 
    <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
                     
          @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
                     
           body {
                animation: fadeIn 1s ease-in-out;
                font-family: 'Quicksand', sans-serif;
                background-color: black;
            }
            
            .q-field__label {
                color: #ffffff !important;
            }
            .q-field--focused .q-field__label {
                color: #ffffff !important;
            }
            .q-field:hover .q-field__label {
                color: #ffffff !important;
            }
    </style>
    """,
                     shared=True
                     )

    # Shoutout to Navisu (underground reference)
    ui.colors(
        primary="#363636",
        secondary="#ffffff",
        accent="#ff4d4d",
        success="#4dff4d",
        warning="#ffff4d",
    )

    ui.button.default_props('no-caps')


def start(readiness_signal: ReadinessSignal) -> None:
    app.readiness_signal = readiness_signal
    ui.run_with(
        app,
        title="LOS Interface",
        # show=False,
        # reload=True,
        dark=True,
        # port=Ports.INTERFACE,
    )


def InterfaceService() -> Service:
    return Service(
        name="Interface Service",
        description="The interface for the LOS system",
        start_func=start,
    )
