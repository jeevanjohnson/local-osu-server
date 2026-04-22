from pathlib import Path

DATA_FOLDER = Path("./.data")

# Json Collections
PROFILES = DATA_FOLDER / "profiles"
BEATMAPS = DATA_FOLDER / "beatmaps"
SCORES = DATA_FOLDER / "scores"

# Json Databases
PORT_STATE = DATA_FOLDER / "port_state.json"
INTERFACE_STATE = DATA_FOLDER / "interface_state.json"
SERVER_SETTINGS = DATA_FOLDER / "server_settings.json"
CLIENT_STATE = DATA_FOLDER / "client_state.json"
LAUNCHER_STATE = DATA_FOLDER / "launcher_state.json"
OSU_FILE_LOCATION = DATA_FOLDER / "osu_file_location.json"
SCORES_LOOKUP = DATA_FOLDER / "scores_lookup.json"
OSU_SCRAPER_STATE = DATA_FOLDER / "osu_scraper_state.json"