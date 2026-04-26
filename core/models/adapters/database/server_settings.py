from jays_tools.sql_database import MigratableSQLModel
from pydantic import Field


class ServerSettingsV1(MigratableSQLModel, table=True):
    osu_api_v2_client_id: int | None = Field(default=None)
    osu_api_v2_client_secret: str | None = Field(default=None)


ServerSettings = ServerSettingsV1
