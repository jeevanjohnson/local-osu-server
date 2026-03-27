from jays_tools.json_database import MigratableModel
from pydantic import Field


class ServerSettingsV1(MigratableModel):
    osu_api_key_v1: str | None = Field(default=None)
    osu_api_v2_client_id: int | None = Field(default=None)
    osu_api_v2_client_secret: str | None = Field(default=None)
    osu_daily_api_key: str | None = Field(default=None)

    auto_update: bool = Field(default=False)  # Needs, git installed on machine

    attempt_beatmap_mirror_downloads: bool = Field(default=False)


CurrentServerSettings = ServerSettingsV1
