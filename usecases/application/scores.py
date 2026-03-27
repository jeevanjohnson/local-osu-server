import usecases.adapters.ossapi
import usecases.application.client.update
import usecases.domain.bancho.scores
import usecases.domain.scores
from models.database.beatmaps import CurrentBeatmap as Beatmap
from models.database.profiles import CurrentProfile as Profile
from models.database.scores import CurrentScore as ProfileScore
from models.domain.accuracy import to_percentage
from models.domain.scores import AcceptedScores, ScoringAlgorithm
from osuProtocol.client_web import (
    Accuracy,
    BeatmapChart,
    MaxCombo,
    OverallRankingChart,
    PerformancePoints,
    Rank,
    RankedScore,
    TotalScore,
)


async def get_ranking_charts(
    beatmap: Beatmap,
    old_profile: Profile,
    current_profile: Profile,
    new_score: ProfileScore,
    scoring_algorithm: ScoringAlgorithm,
    leaderboard_limit: int,
) -> tuple[BeatmapChart, OverallRankingChart]:
    api_client = await usecases.adapters.ossapi.get()
    if not api_client:
        await usecases.application.client.update.restart_client()
        raise Exception("Could not get API client to fetch scores for ranking charts")

    bancho_scores = await usecases.domain.bancho.scores.get_scores_for(
        api_client=api_client,
        beatmap=beatmap,
        game_mode=new_score.game_mode,
        accepted_scores=AcceptedScores.BOTH,  # TODO: unhardcode this w/ parameter
        scoring_algorithm=scoring_algorithm,
    )

    prev_best = await usecases.domain.scores.previous_best_score(
        beatmap=beatmap,
        new_score=new_score,
        scoring_algorithm=scoring_algorithm,
    )

    if prev_best is None:
        rank_entry = Rank(
            before=None,
            after=await usecases.domain.scores.score_rank(
                new_score, bancho_scores, beatmap, scoring_algorithm, leaderboard_limit
            ),
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
        _score_rank = await usecases.domain.scores.score_rank(
            new_score, bancho_scores, beatmap, scoring_algorithm, leaderboard_limit
        )
        _prev_score_rank = await usecases.domain.scores.score_rank(
            prev_best, bancho_scores, beatmap, scoring_algorithm, leaderboard_limit
        )

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
