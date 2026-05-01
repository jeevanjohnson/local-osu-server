from pathlib import Path


class Ports:
    SERVER = 5454
    INTERFACE = 6789


class OsuClient:
    REQUEST_URL = "akatsuki.gg"


class Paths:
    DATA = Path("./.data")
    DATABASE = DATA / "database.db"
    INTERFACE_PID = DATA / "interface.pid"


__all__ = [
    "Ports",
    "OsuClient",
    "Paths"
]
