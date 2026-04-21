
import base64
from jays_tools import MigratableModel
from pydantic import field_serializer, field_validator
from core.models.domain.gameplay.game_mode import GameMode
from core.models.domain.gameplay.mods import Mods
from pydantic import Field

class TotalScoreV1(MigratableModel):
    v1: int
    v2: int

TotalScore = TotalScoreV1

class BeatmapReferenceV1(MigratableModel):
    md5: str
    max_combo: int

    difficulty_adjusted: bool
    original_md5: str

BeatmapReference = BeatmapReferenceV1

class StatisticsV1(MigratableModel):
    total_score: TotalScore
    count_300: int
    count_100: int
    count_50: int
    count_miss: int
    combo: int
    perfect: bool

class ScoreV1(MigratableModel):
    id: int
    profile_name: str
    beatmap: BeatmapReference
    statistics: StatisticsV1
    game_mode: GameMode
    mods: Mods
    pp: int
    replay: bytes
    epoch_time_set_at: int

    @field_serializer("mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)

    @field_validator("mods", mode="before")
    @classmethod
    def deserialize_mods(cls, value: list[str]) -> Mods:
        return Mods(value)

    @field_serializer("replay")
    def serialize_replay(self, value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @field_validator("replay", mode="before")
    @classmethod
    def deserialize_replay(cls, value: str) -> bytes:
        return base64.b64decode(value.encode("ascii"))

    class Config:
        arbitrary_types_allowed=True

Score = ScoreV1

class MapScoresV1(MigratableModel):
    all: list[Score]

MapScores = MapScoresV1

class ScoreLookUpV1(MigratableModel):
    id_to_beatmap_md5: dict[int, str] = Field(default_factory=dict)
    profile_name_to_ids: dict[str, list[int]] = Field(default_factory=dict)

ScoreLookUp = ScoreLookUpV1