from pathlib import Path

DATA = Path("./.data")
RESOURCES = Path("./resources")

PROFILES = DATA / "profiles.json"  # The file where user profiles will be stored
SESSIONS = DATA / "sessions.json"  # The file where session information will be stored
SERVER_SETTINGS = (
    DATA / "server_settings.json"
)  # The file where server settings will be stored
BEATMAPS = (
    DATA / "beatmaps.json"
)  # The file where beatmap information & cache will be stored
OSU_FILES = (
    DATA / "osu_files.json"
)  # The file where osu map/audio payloads are stored by beatmap md5
SCORES = (
    DATA / "scores.json"
)  # The file where submitted scores will be stored before being processed
CACHE_SONGS_FOLDER = (
    DATA / "songs_folder_cache.json"
)  # The file where various cache information will be stored (e.g. beatmap md5 to path, beatmap id to path, etc.)
CLIENT_UPDATES = DATA / "client_updates.json"
CLIENT_STATE = (
    DATA / "client_state.json"
)  # The file where the current state of the client will be
