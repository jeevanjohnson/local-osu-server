"""
Domain/Concept/Purpose:
- This file contains all constants used across the application.
"""
from pathlib import Path

OSU_CLIENT_REQUEST_URL = "akatsuki.gg"  # The URL that the osu! client will request, which we will redirect to localhost
LOS_PORT = 5001  # The port on which the local server will run
LOS_GUI_PORT = 8000  # The port on which the GUI will run
DATA_FOLDER = Path("./.data")
PROFILES_FILE = DATA_FOLDER / "profiles.json"  # The file where user profiles will be stored
SESSIONS_FILE = DATA_FOLDER / "sessions.json"  # The file where session information will be stored