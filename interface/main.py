import subprocess
import sys
import time
import webbrowser
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from nicegui import ui

import core.usecases.domain.port as port_usecases
import interface.usecases.domain.process as process_usecases



def start() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "interface.main"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    process_usecases.set_process_id(process.pid)

    port = port_usecases.assign_port_to("interface")

    print(f"Currently running interface on {port} with PID {process.pid}")

    while True:
        if port_usecases.in_use(port):
            webbrowser.open(f"http://localhost:{port}")
            break
        print(f"Waiting for interface to start on {port}")
        time.sleep(1)


def stop() -> None:
    process_usecases.shutdown()
    port_usecases.clear_port_for("interface")


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

if __name__ in {"__main__", "__mp_main__"}:
    pages = Path(__file__).parent / "pages"
    for page in pages.glob("*.py"):
        module_name = page.stem
        page = __import__(f"interface.pages.{module_name}", fromlist=[module_name])
        try:        
            page.build(template)
        except AttributeError:
            print(f"Page module {module_name} does not have a build function.")
            sys.exit(1)

    port = port_usecases.retrive_port_for("interface")
    if port is None:
        print("No port assigned for interface. Exiting.")
        sys.exit(1)

    ui.run(
        title="LOS Interface",
        show=False,
        reload=True,
        dark=True,
        port=port,
    )