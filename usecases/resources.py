from pathlib import Path

from constants import RESOURCES_FOLDER


def retrive(resource_path: str) -> Path | None:
    path = RESOURCES_FOLDER / resource_path

    if not path.exists() or not path.is_file():
        return None

    return path
