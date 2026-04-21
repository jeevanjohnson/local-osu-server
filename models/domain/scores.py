import random
from enum import Enum, IntEnum

import ossapi.enums

import usecases.domain.calculator.rank
from models.bancho.scores import LazerScore, StableScore
from models.bancho.scores import Score as BanchoScore
from models.database.scores import CurrentScore as ProfileScore


class ScoringAlgorithm(IntEnum):
    SCORE = 0
    PP = 1

    def to_api_v2(self) -> ossapi.enums.RankingType:
        return {
            ScoringAlgorithm.SCORE: ossapi.enums.RankingType.SCORE,
            ScoringAlgorithm.PP: ossapi.enums.RankingType.PERFORMANCE,
        }[self]


class AcceptedScores(Enum):
    LAZER_ONLY = "lazer_only"
    STABLE_ONLY = "stable_only"
    BOTH = "both"


class AllScores(list[BanchoScore | ProfileScore]):
    @property
    def total(self) -> int:
        return len(self)

    def position_of_score(
        self,
        target_score: BanchoScore | ProfileScore,
        scoring_algorithm: ScoringAlgorithm,
        beatmap_pass_count: int,
        leaderboard_limit: int,
    ) -> int:
        """Get the position of a score in the list when sorted by the given scoring algorithm."""
        temp_scores = AllScores(self)
        temp_scores.sort(scoring_algorithm)

        try:
            position = temp_scores.index(target_score) + 1
            if self.total < leaderboard_limit:
                return position

            # This is when we have a total of 51 scores
            last_position = self.total
            if position != last_position:
                print(f"Found target score at position {position} in sorted scores.")
                return position
        except ValueError:
            print(
                "Target score not found in sorted scores, calculating position using scoring algorithm."
            )
            if isinstance(target_score, (StableScore, LazerScore)):
                raise ValueError(
                    "Target score not found in the list of scores. This should not happen since the target score should be included in the list."
                )

        # (position, score) pairs for all scores except the target score
        data_points: list[tuple[int, int]] = []

        for index, score in enumerate(temp_scores):
            if score == target_score:
                continue  # Skip the target score itself

            if scoring_algorithm == ScoringAlgorithm.PP:
                ingame_score = score.performance_points or 0
            else:
                ingame_score = score.total_score

            data_points.append((index + 1, ingame_score))

        # usually the lowest scores on maps typically be around
        # 0 - 20 % acc equalling around 0 - 9500 score
        if scoring_algorithm == ScoringAlgorithm.LAZER:
            data_points.append((beatmap_pass_count, random.randint(0, 9500)))
        elif scoring_algorithm == ScoringAlgorithm.PP:
            # play just worth nothing
            data_points.append((beatmap_pass_count, 0))
        else:
            raise ValueError(f"Unsupported scoring algorithm: {scoring_algorithm}")

        if scoring_algorithm == ScoringAlgorithm.LAZER:
            return usecases.domain.calculator.rank.position_for_score(
                scores_total_score=target_score.total_score,
                data_points=data_points,
            )
        elif scoring_algorithm == ScoringAlgorithm.PP:
            return usecases.domain.calculator.rank.position_for_score(
                scores_total_score=target_score.performance_points or 0,
                data_points=data_points,
            )
        else:
            raise ValueError(f"Unsupported scoring algorithm: {scoring_algorithm}")

    def sort(self, scoring_algorithm: ScoringAlgorithm) -> None:
        if scoring_algorithm == ScoringAlgorithm.PP:
            self.sort_by_pp()
        elif scoring_algorithm == ScoringAlgorithm.LAZER:
            self.sort_by_score()
        else:
            raise ValueError(f"Unsupported scoring algorithm: {scoring_algorithm}")

    def sort_by_pp(self) -> None:

        def pp_key(score: BanchoScore | ProfileScore) -> int:
            return score.performance_points or 0

        super().sort(key=pp_key, reverse=True)

    def sort_by_score(self) -> None:

        def score_key(score: BanchoScore | ProfileScore) -> int:
            return score.total_score or 0

        super().sort(key=score_key, reverse=True)
