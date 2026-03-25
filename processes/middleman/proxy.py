import os

from adapters import log


def proxy_process() -> None:
    log.success("Successfully start proxy server")

    try:
        os.system("mitmdump -s ./processes/middleman/mitm.py -q")
    except KeyboardInterrupt:
        pass
