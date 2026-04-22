
import base64
from jays_tools import MigratableModel
from pydantic import field_serializer, field_validator
from core.models.domain.gameplay.game_mode import GameMode
from core.models.domain.gameplay.mods import Mods
from core.models.domain.gameplay.accuracy import Accuracy
from pydantic import Field

class TotalScoreV1(MigratableModel):
    v1: int = Field(default=0)
    v2: int = Field(default=0)

TotalScore = TotalScoreV1

class BeatmapReferenceV1(MigratableModel):
    md5: str = Field(default="")
    max_combo: int = Field(default=0)

    difficulty_adjusted: bool = Field(default=False)
    original_md5: str = Field(default="")

BeatmapReference = BeatmapReferenceV1

class StatisticsV1(MigratableModel):
    total_score: TotalScore = Field(default_factory=TotalScore)
    count_300: int = Field(default=0)
    count_100: int = Field(default=0)
    count_50: int = Field(default=0)
    count_miss: int = Field(default=0)
    combo: int = Field(default=0)
    perfect: bool = Field(default=False)
    pp: int = Field(default=0)

    @property
    def accuracy(self) -> Accuracy:
        total_hits = self.count_300 + self.count_100 + self.count_50 + self.count_miss
        if total_hits == 0:
            return Accuracy(0.0)
        return Accuracy(
            (self.count_300 * 300 + self.count_100 * 100 + self.count_50 * 50)
            / (total_hits * 300)
        )

Statistics = StatisticsV1

class ScoreV1(MigratableModel):
    id: int = Field(default=0)
    profile_name: str = Field(default_factory=str)
    beatmap: BeatmapReference = Field(default_factory=BeatmapReference)
    statistics: Statistics = Field(default_factory=Statistics)
    game_mode: GameMode = Field(default=GameMode.STANDARD)
    mods: Mods = Field(default_factory=Mods)
    replay: bytes = Field(default=b"")
    epoch_time_set_at: int = Field(default=0)

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
    all: list[Score] = Field(default_factory=list)

MapScores = MapScoresV1

class ScoreLookUpV1(MigratableModel):
    id_to_beatmap_md5: dict[int, str] = Field(default_factory=dict)
    profile_name_to_ids: dict[str, list[int]] = Field(default_factory=dict)

ScoreLookUp = ScoreLookUpV1