from constants import RESOURCES_FOLDER
from pathlib import Path

def retrive(resource_path: str) -> Path | None:
    path = RESOURCES_FOLDER / resource_path

    if not path.exists() or not path.is_file():
        return None

    return path