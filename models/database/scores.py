from jays_tools import MigratableModel
from pydantic import Field

from models.domain.gameplay import Mods
from osuProtocol.server_packets import osuGameMode
from osupyparser.osr.osr_parser import ReplayFile
from adapters import OsuFile

EpochTime = int


class ScoreV1(MigratableModel):
    score_id: int
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

    osu_file: OsuFile
    audio_file: bytes
    replay: ReplayFile

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
            self.combo / self.osu_file.max_combo if self.osu_file.max_combo > 0 else 0
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


class Scores(MigratableModel):
    scores: dict[BEATMAP_MD5, list[CurrentScore]] = Field(default_factory=dict)
