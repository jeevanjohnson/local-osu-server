
import base64
from jays_tools.sql_database import MigratableSQLModel
from pydantic import field_serializer, field_validator
from core.models.domain.normalizers.game_mode import GameMode
from core.models.domain.normalizers.mods import Mods
from core.models.domain.normalizers.accuracy import Accuracy
from pydantic import Field


class ScoreV1(MigratableSQLModel, table=True):
    # identifiers
    profile_name: str = Field(default_factory=str)

    # beatmap details
    beatmap_md5: str = Field(default="")
    beatmap_max_combo: int = Field(default=0)
    beatmap_is_difficulty_adjusted: bool = Field(default=False)
    beatmap_original_md5: str = Field(default="")

    # score details
    game_mode: GameMode = Field(default=GameMode.STANDARD)
    total_score_v1: int = Field(default=0)
    total_score_v2: int = Field(default=0)
    count_300: int = Field(default=0)
    count_100: int = Field(default=0)
    count_50: int = Field(default=0)
    count_miss: int = Field(default=0)
    combo: int = Field(default=0)
    perfect: bool = Field(default=False)
    pp: int = Field(default=0)
    epoch_time_set_at: int = Field(default=0)
    replay: bytes = Field(default=b"")
    mods: Mods = Field(default_factory=Mods)

    @field_serializer("mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)

    @field_validator("mods", mode="before")
    @classmethod
    def deserialize_mods(cls, value: list[str]) -> Mods:
        return Mods.from_list(value)

    @field_serializer("replay")
    def serialize_replay(self, value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @field_validator("replay", mode="before")
    @classmethod
    def deserialize_replay(cls, value: str) -> bytes:
        return base64.b64decode(value.encode("ascii"))

    class Config:
        arbitrary_types_allowed = True

    @property
    def accuracy(self) -> Accuracy:
        total_hits = self.count_300 + self.count_100 + self.count_50 + self.count_miss
        if total_hits == 0:
            return Accuracy(0.0)
        return Accuracy(
            (self.count_300 * 300 + self.count_100 * 100 + self.count_50 * 50)
            / (total_hits * 300)
        )


Score = ScoreV1
