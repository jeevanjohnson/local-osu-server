from jays_tools import MigratableModel
from osupyparser.osr.osr_parser import ReplayFile
from pydantic import ConfigDict, Field, field_serializer, field_validator

from models.domain.gameplay import Mods
from osuProtocol.server_packets import osuGameMode
from usecases.score_submission import ScoreData

EpochTime = int


class ScoreV1(MigratableModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    score_id: int
    beatmap_md5: str
    game_mode: osuGameMode
    username: str
    count50: int
    count100: int
    count300: int
    count_miss: int
    combo: int
    enabled_mods: Mods
    perfect: bool
    time_set: EpochTime
    performance_points: int | None = Field(default=None)
    replay: ReplayFile

    beatmap_max_combo: int

    @field_serializer("enabled_mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)

    @field_validator("enabled_mods", mode="before")
    @classmethod
    def deserialize_mods(cls, value: list[str]) -> Mods:
        return Mods(value)

    @classmethod
    def from_score_submission(
        cls,
        score_id: int,
        score_data: ScoreData,
        beatmap_md5: str,
        replay_file: ReplayFile,
        beatmap_max_combo: int,
    ) -> "ScoreV1":
        # This is where we would calculate the total score based on the score data and beatmap info.
        # For now, we'll just set it to 0 and fill it in later.
        return cls(
            score_id=score_id,  # This will be set when the score is saved to the database
            game_mode=score_data.game_mode,
            username=score_data.username,
            count50=score_data.count_50,
            count100=score_data.count_100,
            count300=score_data.count_300,
            count_miss=score_data.count_miss,
            combo=score_data.max_combo,
            enabled_mods=score_data.mods,
            perfect=score_data.passed,
            time_set=int(score_data.play_time.timestamp()),
            performance_points=None,  # This will be calculated later based on the beatmap and mods
            replay=replay_file,
            beatmap_md5=beatmap_md5,
            beatmap_max_combo=beatmap_max_combo,
        )

    @property
    def total_score(self) -> int:
        # Note: bonus_points only comes from spinner over-spin (not implemented here)
        bonus_points: float = 0.0

        total_hits = self.count300 + self.count100 + self.count50 + self.count_miss

        if total_hits == 0:
            return 0

        # Accuracy calculation (standard osu! weighting)
        accuracy = (self.count300 + self.count100 / 3 + self.count50 / 5) / total_hits

        # Combo progress: achieved combo / max possible combo
        combo_progress = (
            self.combo / self.beatmap_max_combo if self.beatmap_max_combo > 0 else 0
        )

        # Accuracy progress: in osu!standard this is always 1.0
        accuracy_progress = 1.0

        # Correct lazer scoring formula (two 500k terms)
        hit_score = (
            500_000 * accuracy * combo_progress
            + 500_000 * (accuracy**5) * accuracy_progress
        )

        # Add bonus points (spinner overspins)
        base_score = hit_score + bonus_points

        # Apply the 0.96× "Classic" multiplier (always present for imported scores)
        # Then apply any mod multiplier from the original play (DT, HT, etc.)
        final_score = (
            base_score * 0.96 * self.enabled_mods.mod_multipler(self.game_mode)
        )

        return round(final_score)


CurrentScore = ScoreV1

BEATMAP_MD5 = str


class ScoresV1(MigratableModel):
    scores: dict[BEATMAP_MD5, list[CurrentScore]] = Field(default_factory=dict)

    @property
    def total_scores(self) -> int:
        return sum(len(scores) for scores in self.scores.values())


CurrentScores = ScoresV1
