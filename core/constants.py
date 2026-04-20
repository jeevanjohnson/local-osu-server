from pathlib import Path

DATA_FOLDER = Path("./.data")

# Json Collections
PROFILES = DATA_FOLDER / "profiles"

# Json Databases
PORT_STATE = DATA_FOLDER / "port_state.json"
INTERFACE_STATE = DATA_FOLDER / "interface_state.json"
SERVER_SETTINGS = DATA_FOLDER / "server_settings.json"
CLIENT_STATE = DATA_FOLDER / "client_state.json"
LAUNCHER_STATE = DATA_FOLDER / "launcher_state.json"