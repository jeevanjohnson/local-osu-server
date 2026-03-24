"""
Purpose/Domain/Concept:
- Runs all the necessary services for the application.
"""

from install_dependencies import install_dependencies

install_dependencies()

import asyncio  # noqa: E402
import multiprocessing  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
from typing import Callable  # noqa: E402

import uvicorn  # noqa: E402
import webview  # noqa: E402

from constants import LOS_GUI_PORT, LOS_PORT  # noqa: E402

PROCESSES: dict[str, multiprocessing.Process] = {}


def _run_with_graceful_shutdown(func: Callable) -> None:
    try:
        func()
    except KeyboardInterrupt:
        print("Shutting down gracefully...")


def process(func: Callable, daemon: bool = True) -> Callable:
    PROCESSES[func.__name__] = multiprocessing.Process(
        target=_run_with_graceful_shutdown, args=(func,), daemon=daemon
    )

    return func


@process
def middleman_proxy():
    print("Proxy server is running!")

    os.system("mitmdump -s middleman.py -q")


@process
def local_server():
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=LOS_PORT,
        # access_log=False,
        # log_level="critical",
    )


@process
def gui():
    os.system(f"{sys.executable} gui.py")


@process
def open_gui():
    import usecases.sessions

    if asyncio.run(usecases.sessions.session_exists()):
        url = f"http://localhost:{LOS_GUI_PORT}/dashboard"
    else:
        url = f"http://localhost:{LOS_GUI_PORT}/"

    webview.create_window(
        title="Los!",
        url=url,
        resizable=True,
        frameless=True,
        draggable=True,
    )
    webview.start()


def start_services():
    for process_name, process in PROCESSES.items():
        print(f"Starting {process_name}...")
        process.start()


def keep_alive():
    for process_name, process in PROCESSES.items():
        process.join()  # Wait for the process to finish, overwritten with daemon=True,
        # so it will run until the main process is killed

        print(f"{process_name} has stopped.")


def shutdown_services():
    print("Shutting down all services...")
    for process_name, process in PROCESSES.items():
        if process.is_alive():
            print(f"Terminating {process_name}...")
            process.terminate()
            process.join()
    print("All services have been shut down.")


def main():
    start_services()

    try:
        keep_alive()
    except KeyboardInterrupt:
        print("Shutting down all services...")
        shutdown_services()
        print("All services have been shut down.")


if __name__ == "__main__":
    main()
