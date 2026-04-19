import subprocess
import sys
import webbrowser
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from nicegui import ui

import interface.usecases.domain.port as port_usecases
import interface.usecases.domain.process as process_usecases


def start() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "interface.main"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    process_usecases.set_process_id(process.pid)

    port = port_usecases.get()

    print(f"Currently running interface on {port} with PID {process.pid}")

    webbrowser.open(f"http://localhost:{port}")


def stop() -> None:
    process_usecases.shutdown()
    port_usecases.clear()


if __name__ in {"__main__", "__mp_main__"}:
    pages = Path(__file__).parent / "pages"
    for page in pages.glob("*.py"):
        module_name = page.stem
        page = __import__(f"interface.pages.{module_name}", fromlist=[module_name])

        try:
            page.build()
        except AttributeError:
            print(f"Page module {module_name} does not have a build function.")
            sys.exit(1)

    ui.run(
        title="LOS Interface",
        show=False,
        reload=False,
        dark=True,
        port=port_usecases.get(),
    )