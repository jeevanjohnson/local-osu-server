from repositories.server_settings import ServerSettingsRepository
from constants import SERVER_SETTINGS_FILE
from ossapi import Beatmapset, Ossapi
from ossapi import Beatmap

class ApiV2CredentialsError(Exception):
    pass

def get_ossapi() -> Ossapi:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = server_settings_repo.get_server_settings()
    if server_settings is None:
        raise ValueError("Server settings not found. This should never happen, please contact the developer.")
    
    if server_settings["osu_api_v2_client_id"] is None or server_settings["osu_api_v2_client_secret"] is None:
        raise ApiV2CredentialsError("osu! API v2 credentials not found in server settings. Please set them up in the server settings page.")

    try:
        client_id = int(server_settings["osu_api_v2_client_id"])
    except ApiV2CredentialsError:
        raise ApiV2CredentialsError("Invalid osu! API v2 client ID in server settings. Please ensure it's a valid integer.")

    client_secret = server_settings["osu_api_v2_client_secret"]

    osuApi = Ossapi(client_id, client_secret)

    return osuApi

def get_beatmap_from_md5(beatmap_md5: str) -> Beatmap | None:
    osuApi = get_ossapi()
    try:
        beatmap = osuApi.beatmap(checksum=beatmap_md5)
    except ValueError:
        return None
    
    if not beatmap:
        return None
    
    return beatmap

def get_beatmap_from_id(beatmap_id: int) -> Beatmap | None:
    osuApi = get_ossapi()
    try:
        beatmap = osuApi.beatmap(beatmap_id=beatmap_id)
    except ValueError:
        return None

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

def get_beatmapset_from_id(beatmap_set_id: int) -> Beatmapset | None:
    osuApi = get_ossapi()
    try:
        beatmap_set = osuApi.beatmapset(beatmapset_id=beatmap_set_id)
    except ValueError:
        return None
    
    if not beatmap_set:
        return None
    
    return beatmap_set

def get_beatmap_set_from_md5(beatmap_md5: str) -> Beatmapset | None:
    beatmap = get_beatmap_from_md5(beatmap_md5)
    if beatmap is None:
        return None
    
    beatmap_set = get_beatmapset_from_id(beatmap.beatmapset_id)
    return beatmap_set

def get_beatmap_set_from_beatmap_id(beatmap_id: int) -> Beatmapset | None:
    beatmap = get_beatmap_from_id(beatmap_id)
    if beatmap is None:
        return None
    
    beatmap_set = get_beatmapset_from_id(beatmap.beatmapset_id)
    return beatmap_set

def get_beatmap_set(
    beatmap_md5: str | None = None,
    beatmap_id: int | None = None,
    beatmap_set_id: int | None = None
) -> Beatmapset | None:
    
    if beatmap_set_id is not None:
        beatmap_set = get_beatmapset_from_id(beatmap_set_id)
        if beatmap_set:
            return beatmap_set
    
    if beatmap_md5 is not None:
        beatmap_set = get_beatmap_set_from_md5(beatmap_md5)
        if beatmap_set:
            return beatmap_set
    
    if  beatmap_id is not None:
        beatmap_set = get_beatmap_set_from_beatmap_id(beatmap_id)
        if beatmap_set:
            return beatmap_set
   
    return None