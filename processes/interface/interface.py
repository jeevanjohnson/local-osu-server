import os
import sys
import webbrowser

from adapters import log
from constants import DEVELOPER_MODE, LOS_INTERFACE_PORT


def interface_process() -> None:
    if DEVELOPER_MODE:
        log.success("Running interface process in developer mode!")
        log.success(
            f"!!!!!!!!!!!!! INTERFACE CAN BE FOUND HERE: http://localhost:{LOS_INTERFACE_PORT}/ !!!!!!!!!!!!!!!"
        )
    else:
        webbrowser.open_new_tab(f"http://localhost:{LOS_INTERFACE_PORT}/")

    try:
        os.system(f"{sys.executable} interface.py")
    except KeyboardInterrupt:
        pass
