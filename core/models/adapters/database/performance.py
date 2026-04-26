from pydantic import Field, field_validator
from core.models.domain.normalizers.game_mode import GameMode
from core.models.domain.normalizers.accuracy import Accuracy
from jays_tools.sql_database import MigratableSQLModel


class PerformanceV1(MigratableSQLModel, table=True):
    profile_name: str = Field(default="")
    game_mode: GameMode = Field(default=GameMode.STANDARD)
    rank: int = Field(default=0)
    accuracy: Accuracy = Field(default=Accuracy(0))
    playcount: int = Field(default=0)
    total_score_v1: int = Field(default=0)
    total_score_v2: int = Field(default=0)
    ranked_score_v1: int = Field(default=0)
    ranked_score_v2: int = Field(default=0)
    performance_points: int = Field(default=0)
    max_combo: int = Field(default=0)

    @field_validator("accuracy", mode="before")
    @classmethod
    def normalize_accuracy(cls, value: float | int) -> Accuracy:
        return Accuracy(value)

    class Config:
        arbitrary_types_allowed = True


Performance = PerformanceV1
