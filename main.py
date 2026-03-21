"""
Purpose/Domain/Concept:
- Runs all the necessary services for the application.
"""

from install_dependencies import install_dependencies

install_dependencies()

import multiprocessing
import os
import sys
from typing import Callable

import uvicorn
import webview

from constants import LOS_GUI_PORT, LOS_PORT

PROCESSES: dict[str, multiprocessing.Process] = {}


def _run_with_graceful_shutdown(func: Callable) -> None:
    try:
        func()
    except KeyboardInterrupt:
        print("Shutting down gracefully...")


def graceful_shutdown(func: Callable, daemon: bool = True) -> Callable:
    PROCESSES[func.__name__] = multiprocessing.Process(
        target=_run_with_graceful_shutdown, args=(func,), daemon=daemon
    )

    return func


@graceful_shutdown
def middleman_proxy():
    print("Proxy server is running!")

    os.system("mitmdump -s middleman.py -q")


@graceful_shutdown
def local_server():
    uvicorn.run("server:app", host="127.0.0.1", port=LOS_PORT)


@graceful_shutdown
def gui():
    os.system(f"{sys.executable} gui.py")


@graceful_shutdown
def open_gui():
    import usecases.sessions

    if usecases.sessions.session_exists():
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
