"""
Domain/Concept/Purpose:
- This file contains all constants used across the application.
"""

from pathlib import Path

OSU_CLIENT_REQUEST_URL = "akatsuki.gg"  # The URL that the osu! client will request, which we will redirect to localhost
LOS_PORT = 5001  # The port on which the local server will run
LOS_INTERFACE_PORT = 8000  # The port on which the GUI will run
DATA_FOLDER = Path("./.data")
RESOURCES_FOLDER = Path("./resources")
PROFILES_FILE = (
    DATA_FOLDER / "profiles.json"
)  # The file where user profiles will be stored
SESSIONS_FILE = (
    DATA_FOLDER / "sessions.json"
)  # The file where session information will be stored
SERVER_SETTINGS_FILE = (
    DATA_FOLDER / "server_settings.json"
)  # The file where server settings will be stored
BEATMAPS_FILE = (
    DATA_FOLDER / "beatmaps.json"
)  # The file where beatmap information & cache will be stored
OSU_FILES_FILE = (
    DATA_FOLDER / "osu_files.json"
)  # The file where osu map/audio payloads are stored by beatmap md5
SCORES_FILE = (
    DATA_FOLDER / "scores.json"
)  # The file where submitted scores will be stored before being processed
CACHE_SONGS_FOLDER_FILE = (
    DATA_FOLDER / "songs_folder_cache.json"
)  # The file where various cache information will be stored (e.g. beatmap md5 to path, beatmap id to path, etc.)
SEASONAL_BG_GIT_URL = "https://raw.githubusercontent.com/jeevanjohnson/local-osu-server/refs/heads/2026/resources/seasonal_bg.png"

if Path.cwd().name == "LOS2026":
    DEVELOPER_MODE = True
else:
    DEVELOPER_MODE = False
