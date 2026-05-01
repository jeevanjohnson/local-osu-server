import sys  # noqa
from pathlib import Path  # noqa

sys.path.append(str(Path(__file__).parent.parent))  # noqa

from nicegui import ui
from constants import Ports
from jays_tools.services import Service, ReadinessSignal
import subprocess
from constants import Paths
from interface.repositories.process import ProcessRepository

PROCESS_REPOSITORY = ProcessRepository()


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

    ui.separator.default_style(
        "color: white; "
    )


def stop() -> None:
    pid = PROCESS_REPOSITORY.get_process_id()

    if pid is not None:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            print(f"Failed to stop interface service with PID {pid}")

        PROCESS_REPOSITORY.clear_process_id()


def start(readiness_signal: ReadinessSignal) -> None:
    process = subprocess.Popen([
        sys.executable, "-m", "interface.service"
    ])
    PROCESS_REPOSITORY.save_process_id(process.pid)
    readiness_signal.set()


def InterfaceService() -> Service:
    return Service(
        name="Interface Service",
        description=f"The interface for the LOS system, you can find here: http://localhost:{Ports.INTERFACE}",
        start_func=start,
        stop_func=stop,
    )


if __name__ in {
    "__main__",
    "__mp_main__"
}:
    pages = Path(__file__).parent / "pages"
    for page in pages.glob("*.py"):
        module_name = page.stem
        print("loading", module_name)
        page = __import__(
            f"interface.pages.{module_name}", fromlist=[module_name])

        try:
            page.build(template)
        except AttributeError:
            print(
                f"Page module {module_name} does not have a build function."
            )
            sys.exit(1)

    ui.run(
        title="LOS Interface",
        show=False,
        reload=False,
        dark=True,
        port=Ports.INTERFACE,
    )
