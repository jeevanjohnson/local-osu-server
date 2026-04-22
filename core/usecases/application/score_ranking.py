"""
Application use cases for calculating score rankings and positions.
"""

import ossapi.models
from core.models.database.beatmaps import Beatmap
from core.models.database.scores import Score
from core.models.domain.gameplay.scoring import ScoringType
import core.usecases.domain.calculator.position as score_position_calculator_usecases
import core.usecases.domain.beatmap as domain_beatmap_usecases
import core.usecases.domain.scores as scores_usecases


async def get_score_position(
    score: Score,
    beatmap: Beatmap,
    bancho_scores: list[ossapi.models.Score],
    scoring_type: ScoringType,
) -> int:
    """
    Calculate the leaderboard position of a score.
    
    This function determines if a score ranks within the provided bancho scores
    (top leaderboard), or uses interpolation to estimate position for scores
    outside the leaderboard.
    
    Args:
        score: The player's score
        beatmap: The beatmap the score is on
        bancho_scores: List of top scores from osu! API
        scoring_type: How scores are sorted (PP, ScoreV1, ScoreV2)
    
    Returns:
        The calculated position on the beatmap leaderboard
    """
    print(f"[GET_POSITION] Getting position for {score.profile_name} on beatmap {beatmap.md5}")
    print(f"[GET_POSITION] Beatmap status: {beatmap.status}, Bancho scores count: {len(bancho_scores)}")
    
    # Extract sorting values from bancho scores
    ranking: list[tuple[str, int]] = []

    for bancho_score in bancho_scores:
        if scoring_type == ScoringType.SCOREV1:
            score_value = bancho_score.classic_total_score
        elif scoring_type == ScoringType.SCOREV2:
            score_value = bancho_score.total_score
        else:  # ScoringType.PP
            if bancho_score.pp is None:
                score_value = 0
            else:
                score_value = int(bancho_score.pp)

        ranking.append(("not_me", score_value))
    
    # Extract this player's score value
    if scoring_type == ScoringType.SCOREV1:
        my_score_value = score.statistics.total_score.v1
    elif scoring_type == ScoringType.SCOREV2:
        my_score_value = score.statistics.total_score.v2
    else:  # ScoringType.PP
        my_score_value = score.statistics.pp
    
    print(f"[GET_POSITION] My score value: {my_score_value}, Scoring type: {scoring_type}")
    print(f"[GET_POSITION] Leaderboard has {len(ranking)} scores")
    
    # Get total scores on beatmap
    if beatmap.status.has_leaderboards():
        total_scores = await domain_beatmap_usecases.get_pass_count(beatmap)
    else:
        total_scores = len(
            scores_usecases.get_map_scores_for(score.profile_name, beatmap.md5)
        )
    
    print(f"[GET_POSITION] Total scores on beatmap: {total_scores}")
    
    # Check if this score is within the bancho scores (not below all of them)
    my_tuple = ("me", my_score_value)
    test_ranking = ranking + [my_tuple]
    test_ranking.sort(key=lambda x: x[1], reverse=True)
    
    # Find where our score ranks among all leaderboard scores
    position_in_leaderboard = None
    for idx in range(len(test_ranking)):
        if test_ranking[idx] == my_tuple:
            position_in_leaderboard = idx + 1
            break
    
    # If score is within the leaderboard scores (not below all of them), return that position
    if position_in_leaderboard is not None and position_in_leaderboard <= len(ranking):
        print(f"[GET_POSITION] ✓ Found in leaderboard, position: #{position_in_leaderboard}")
        return position_in_leaderboard
    
    print(f"[GET_POSITION] ❌ Score is below all leaderboard scores, using interpolation")

    # Use interpolation for scores outside the top leaderboard
    position = score_position_calculator_usecases.get_leaderboard_position(
        sorting_value=my_score_value,
        leaderboard_scores=[
            (score[1], idx + 1) for idx, score in enumerate(ranking)  # (sorting_value, position)
        ],
        total_scores=total_scores
    )
    
    print(f"[GET_POSITION] Calculated position from calculator: #{position}")
    return position if position > 0 else 1
