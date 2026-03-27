import os
import sys
import webbrowser

from constants.network import LOS_INTERFACE_PORT


def interface_process() -> None:
    webbrowser.open_new_tab(f"http://localhost:{LOS_INTERFACE_PORT}/")
    try:
        os.system(f"{sys.executable} interface.py")
    except KeyboardInterrupt:
        pass
