from datetime import datetime

from jays_tools.sql_database import MigratableSQLModel
from pydantic import Field

from core.models.domain.normalizers.game_mode import GameMode
from core.models.domain.normalizers.rank_status import RankStatus


class BeatmapV1(MigratableSQLModel, table=True):
    md5: str = Field(default="")
    id: int = Field(default=0)
    set_id: int = Field(default=0)

    difficulty_adjusted: bool = Field(default=False)
    original_beatmap_md5: str = Field(default="")

    # metadata
    artist: str = Field(default="")
    title: str = Field(default="")
    version: str = Field(default="")

    # bmap details
    max_combo: int = Field(default=0)
    mode: GameMode = Field(default=GameMode.STANDARD)
    cs: float = Field(default=0.0)
    ar: float = Field(default=0.0)
    hp: float = Field(default=0.0)
    od: float = Field(default=0.0)
    # object_count: int = Field(default=0)
    # drain_time_seconds: int = Field(default=0)

    play_count: int = Field(default=0)
    play_count_timestamp: datetime = Field(default_factory=datetime.now)
    pass_count: int = Field(default=0)
    pass_count_timestamp: datetime = Field(default_factory=datetime.now)

    last_updated: datetime = Field(default_factory=datetime.now)

    status: RankStatus = Field(default=RankStatus.UNSUBMITTED)
    status_timestamp: datetime = Field(default_factory=datetime.now)
    status_override: dict[str, RankStatus] = Field(default_factory=dict)


Beatmap = BeatmapV1
