from jays_tools.json_database import MigratableModel
from pydantic import Field

class ServerSettingsV1(MigratableModel):
    osu_api_v2_client_id: int | None = Field(default=None)
    osu_api_v2_client_secret: str | None = Field(default=None)

ServerSettings = ServerSettingsV1