import usecases.bancho_scores
from adapters.log import log_time
from constants import SCORES_FILE
from models.bancho.scores import (
    Score as BanchoScore,
)
from models.bancho.scores import (
    Scores as BanchoScores,
)
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
from models.database.profiles import (
    CurrentProfile as Profile,
)
from models.database.profiles import (
    CurrentSettings as Settings,
)
from models.database.scores import (
    CurrentMapScores as MapScores,
)
from models.database.scores import (
    CurrentScore as ProfileScore,
)
from models.domain.accuracy import to_percentage
from models.domain.gameplay import Mods, osuGameMode
from osuProtocol.client_web import (
    Accuracy,
    MaxCombo,
    PerformancePoints,
    Rank,
    RankedScore,
    ScoringAlgorithm,
    TotalScore,
)
from osuProtocol.client_web import Beatmap as BeatmapChart
from osuProtocol.client_web import OverallRanking as OverallRankingChart
from osuProtocol.replay import extract_replay_frames_from_osr
from repositories.scores import ScoresRepository
from usecases.bancho_scores import AcceptedScores


class AllScores(list[BanchoScore | ProfileScore]):
    @property
    def total(self) -> int:
        return len(self)

    def position_of_score(
        self,
        target_score: BanchoScore | ProfileScore,
        scoring_algorithm: ScoringAlgorithm,
    ) -> int:
        """Get the position of a score in the list when sorted by the given scoring algorithm."""
        temp_scores = AllScores(self)
        temp_scores.sort(scoring_algorithm)

        try:
            return temp_scores.index(target_score) + 1
        except ValueError:
            return -1

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


async def generate_score_id() -> int:
    """Atomically allocate next score ID"""
    scores_repo = ScoresRepository(SCORES_FILE)
    return await scores_repo.allocate_score_id()


async def get_scores_for_beatmap_from(
    beatmap_md5: str, profile_name: str | None = None
) -> MapScores:
    """Get scores for beatmap. If profile_name provided, get only that profile's scores."""
    scores_repo = ScoresRepository(SCORES_FILE)

    if profile_name:
        map_scores = await scores_repo.get_scores_by_profile_and_beatmap_md5(
            profile_name, beatmap_md5
        )
    else:
        map_scores = await scores_repo.get_leaderboard_for_beatmap(beatmap_md5)

    return map_scores


async def get_scores_for_beatmap(
    beatmap: Beatmap,
    profile_name: str | None = None,
    game_mode: osuGameMode | None = None,
) -> MapScores:
    """Get scores for beatmap. If profile_name provided, get only that profile's scores."""
    map_scores = await get_scores_for_beatmap_from(beatmap.md5, profile_name)

    if game_mode is not None:
        map_scores = map_scores.filter_by(game_mode=game_mode)

    return map_scores


@log_time
async def score_rank(
    score: ProfileScore,
    beatmap: Beatmap,
    settings: Settings,
) -> int:
    if settings.leaderboard.show_lazer_scores_on_leaderboard:
        accepted_scores = AcceptedScores.BOTH
    else:
        accepted_scores = AcceptedScores.STABLE_ONLY

    bancho_scores = await usecases.bancho_scores.get_any_scores_for(
        beatmap=beatmap,
        game_mode=score.game_mode,
        accepted_scores=accepted_scores,
        ranking_type=settings.scoring_algorithm.to_api_v2(),
    )

    if not bancho_scores.all_scores:
        return 1

    all_scores = AllScores()
    all_scores.extend(bancho_scores.all_scores)
    all_scores.append(score)

    return all_scores.position_of_score(score, settings.scoring_algorithm)


@log_time
async def previous_best_score(
    beatmap: Beatmap,
    new_score: ProfileScore,
    settings: Settings,
) -> ProfileScore | None:
    """Get the previous best score for this user on this beatmap.

    This is called after submission, so the repository can already contain
    new_score. We must exclude it, otherwise the first-ever play is treated as
    if it had a previous score.
    """
    map_scores = await get_scores_for_beatmap(
        beatmap=beatmap,
        profile_name=new_score.username,
        game_mode=new_score.game_mode,
    )

    if not map_scores.scores:
        return None

    existing_scores = [score for score in map_scores.scores if score.id != new_score.id]
    if not existing_scores:
        return None

    temp_map = MapScores(beatmap_md5=beatmap.md5, scores=existing_scores)
    temp_map.sort(settings.scoring_algorithm)
    return temp_map.scores[0]


@log_time
async def get_ranking_charts(
    beatmap: Beatmap,
    old_profile: Profile,
    current_profile: Profile,
    new_score: ProfileScore,
    settings: Settings,
) -> tuple[BeatmapChart, OverallRankingChart]:
    prev_best = await previous_best_score(
        beatmap=beatmap,
        new_score=new_score,
        settings=settings,
    )

    if prev_best is None:
        _score_rank = await score_rank(new_score, beatmap, settings)
        if _score_rank == 101:
            _score_rank = None

        rank_entry = Rank(
            before=None,
            after=_score_rank,
        )

        ranked_score_entry = RankedScore(
            before=None,
            after=new_score.total_score,
        )

        total_score_entry = TotalScore(
            before=None,
            after=new_score.total_score,
        )

        max_combo_entry = MaxCombo(
            before=None,
            after=new_score.combo,
        )

        accuracy_entry = Accuracy(
            before=None,
            after=to_percentage(new_score.accuracy),
        )

        pp_entry = PerformancePoints(
            before=None,
            after=new_score.performance_points,
        )
    else:
        _score_rank = await score_rank(new_score, beatmap, settings)
        _prev_score_rank = await score_rank(prev_best, beatmap, settings)

        rank_entry = Rank(
            before=_prev_score_rank,
            after=_score_rank,
        )

        ranked_score_entry = RankedScore(
            before=prev_best.total_score,
            after=new_score.total_score,
        )

        total_score_entry = TotalScore(
            before=prev_best.total_score,
            after=new_score.total_score,
        )

        max_combo_entry = MaxCombo(
            before=prev_best.combo,
            after=new_score.combo,
        )

        accuracy_entry = Accuracy(
            before=to_percentage(prev_best.accuracy),
            after=to_percentage(new_score.accuracy),
        )

        pp_entry = PerformancePoints(
            before=prev_best.performance_points,
            after=new_score.performance_points,
        )

    beatmap_chart = BeatmapChart(
        rank=rank_entry,
        ranked_score=ranked_score_entry,
        total_score=total_score_entry,
        max_combo=max_combo_entry,
        accuracy=accuracy_entry,
        pp=pp_entry,
    )

    rank_entry = Rank(
        before=old_profile.performance[new_score.game_mode].rank,
        after=current_profile.performance[new_score.game_mode].rank,
    )

    ranked_score_entry = RankedScore(
        before=old_profile.performance[new_score.game_mode].ranked_score,
        after=current_profile.performance[new_score.game_mode].ranked_score,
    )

    total_score_entry = TotalScore(
        before=old_profile.performance[new_score.game_mode].total_score,
        after=current_profile.performance[new_score.game_mode].total_score,
    )

    max_combo_entry = MaxCombo(
        before=old_profile.performance[new_score.game_mode].max_combo,
        after=current_profile.performance[new_score.game_mode].max_combo,
    )

    accuracy_entry = Accuracy(
        before=to_percentage(old_profile.performance[new_score.game_mode].accuracy),
        after=to_percentage(current_profile.performance[new_score.game_mode].accuracy),
    )

    pp_entry = PerformancePoints(
        before=old_profile.performance[new_score.game_mode].performance_points,
        after=current_profile.performance[new_score.game_mode].performance_points,
    )

    overall_ranking_chart = OverallRankingChart(
        rank=rank_entry,
        ranked_score=ranked_score_entry,
        total_score=total_score_entry,
        max_combo=max_combo_entry,
        accuracy=accuracy_entry,
        pp=pp_entry,
    )

    return beatmap_chart, overall_ranking_chart


@log_time
async def personal_best_for_beatmap(
    beatmap: Beatmap,
    profile_name: str,
    game_mode: osuGameMode,
    scoring_algorithm: ScoringAlgorithm,
    mods: Mods | None = None,
) -> ProfileScore | None:
    """Get the personal best score for a beatmap and profile."""
    scores_repo = ScoresRepository(SCORES_FILE)

    map_scores = await scores_repo.get_scores_by_profile_and_beatmap_md5(
        profile_name, beatmap.md5
    )

    if not map_scores:
        return None

    filtered_scores = map_scores.filter_by(
        game_mode=game_mode,
        mods=mods,
    )

    if not filtered_scores:
        return None

    if not filtered_scores.scores:
        return None

    filtered_scores.sort(scoring_algorithm)

    return filtered_scores.scores[0]


@log_time
def leaderboard_position(
    personal_best: ProfileScore,
    scores: BanchoScores | MapScores,
    settings: Settings,
) -> int:
    """Calculate the leaderboard position of a score given the current leaderboard scores.

    This is used to determine whether to show the "New #X on the leaderboard!" message after a score submission.
    """

    all_scores = AllScores()

    if isinstance(scores, BanchoScores):
        all_scores.extend(scores.all_scores)
    else:
        all_scores.extend(scores.scores)

    all_scores.append(personal_best)

    all_scores.sort(settings.scoring_algorithm)

    return all_scores.index(personal_best) + 1


@log_time
async def get_replay_frames_for_score_id(score_id: int) -> bytes | None:
    """Get replay frames for a given score ID, if available."""
    scores_repo = ScoresRepository(SCORES_FILE)

    score = await scores_repo.get_score_by_id(
        score_id
    )  # Ensure score exists; raises if not found

    if score is None:
        return None

    if score.replay_frames is None:
        return None

    try:
        return extract_replay_frames_from_osr(score.replay_frames)[0]
    except Exception:
        # Already in form?
        return score.replay_frames
