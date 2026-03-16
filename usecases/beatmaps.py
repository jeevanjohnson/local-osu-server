from repositories.server_settings import ServerSettingsRepository
from constants import SERVER_SETTINGS_FILE
from ossapi import Ossapi
from ossapi import Beatmap

def get_ossapi() -> Ossapi:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = server_settings_repo.get_server_settings()
    if server_settings is None:
        raise ValueError("Server settings not found. This should never happen, please contact the developer.")
    
    if server_settings["osu_api_v2_client_id"] is None or server_settings["osu_api_v2_client_secret"] is None:
        raise ValueError("osu! API v2 credentials not found in server settings. Please set them up in the server settings page.")

    try:
        client_id = int(server_settings["osu_api_v2_client_id"])
    except ValueError:
        raise ValueError("Invalid osu! API v2 client ID in server settings. Please ensure it's a valid integer.")

    client_secret = server_settings["osu_api_v2_client_secret"]

    osuApi = Ossapi(client_id, client_secret)

    return osuApi

def get_beatmap_from_md5(beatmap_md5: str) -> Beatmap | None:
    osuApi = get_ossapi()
    beatmap = osuApi.beatmap(checksum=beatmap_md5)
    if not beatmap:
        return None
    
    return beatmap

def get_beatmap_from_id(beatmap_id: int) -> Beatmap | None:
    osuApi = get_ossapi()
    beatmap = osuApi.beatmap(beatmap_id=beatmap_id)
    if not beatmap:
        return None
    
    return beatmap

def get_beatmap(
    beatmap_md5: str | None = None,
    beatmap_id: int | None = None,
) -> Beatmap | None:
    
    if beatmap_md5 is not None:
        beatmap = get_beatmap_from_md5(beatmap_md5)
        if beatmap:
            return beatmap
    
    if  beatmap_id is not None:
        beatmap = get_beatmap_from_id(beatmap_id)
        if beatmap:
            return beatmap
   
    return None