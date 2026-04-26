from jays_tools.architecture import AdapterModel
from jays_tools.sql_database import MigratableSQLModel
from datetime import datetime
from pydantic import Field

class SnapShotV1(AdapterModel, MigratableSQLModel, table=True):
    osu: list[tuple[int, int]]  = []
    taiko: list[tuple[int, int]] = []
    catch: list[tuple[int, int]] = []
    mania: list[tuple[int, int]] = []
    created_at: datetime = Field(default_factory=datetime.now)

SnapShot = SnapShotV1