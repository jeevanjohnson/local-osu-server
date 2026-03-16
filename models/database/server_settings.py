from typing import TypedDict

class ServerSettings(TypedDict):
    osu_api_key_v1: str | None
    osu_api_v2_client_id: str | None
    osu_api_v2_client_secret: str | None