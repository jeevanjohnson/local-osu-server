"""
Purpose/Domain/Concept: 
- Runs all the necessary services for the application.
"""

from install_dependencies import install_dependencies

install_dependencies()

import multiprocessing
import uvicorn
import os
from constants import LOS_PORT, LOS_GUI_PORT
import sys
import webview

def run_middleman_proxy():
    print("Proxy server is running!")
    try:
        os.system("mitmdump -s middleman.py -q")
    except KeyboardInterrupt:
        pass

def run_local_server():
    uvicorn.run(
        "server:app", 
        host="127.0.0.1", 
        port=LOS_PORT
    )

def run_gui_web():
    try:
        os.system(f"{sys.executable} gui.py")
    except KeyboardInterrupt:
        pass

def open_gui():
    import usecases.sessions

    if usecases.sessions.session_exists():
        url = f"http://localhost:{LOS_GUI_PORT}/dashboard"
    else:
        url = f"http://localhost:{LOS_GUI_PORT}/"

    try:
        webview.create_window(
            title = 'Los!', 
            url = url,
            resizable = True,
            frameless=True,
            draggable=True,
        )
        webview.start()
    except KeyboardInterrupt:
        pass

def run_application():
    process = [
        multiprocessing.Process(target=run_middleman_proxy, daemon=True),
        multiprocessing.Process(target=run_local_server),
        multiprocessing.Process(target=run_gui_web),
        multiprocessing.Process(target=open_gui, daemon=True)
    ]
    for p in process:
        p.start()

    try:
        for p in process:
            p.join()
    except KeyboardInterrupt:
        for p in process:
            p.terminate()

if __name__ == "__main__":
    run_application()
