import usecases.osu_daily
from adapters import log
from models.domain.gameplay import osuGameMode

PP = int
RANK = int


# Linear interpolation
def local_rank_for_pp(pp: PP, points: list[tuple[PP, RANK]]) -> RANK:
    """
    Estimate rank for given PP using linear interpolation of known points.

    Args:
        pp: Performance points value
        points: List of known PP-RANK pairs, sorted by PP descending (highest PP first)

    Returns:
        Estimated rank (as integer)
    """
    # Handle edge cases
    if pp >= points[0][0]:
        return points[0][1]
    if pp <= points[-1][0]:
        return points[-1][1]

    # Find the two points that bracket pp and interpolate
    for i in range(len(points) - 1):
        pp1, rank1 = points[i]
        pp2, rank2 = points[i + 1]

        if pp2 <= pp <= pp1:
            t = (pp1 - pp) / (pp1 - pp2)  # t=0 at pp1, t=1 at pp2
            rank = rank1 + t * (rank2 - rank1)
            return int(round(rank))

    # Fallback to highest rank (shouldn't reach here if POINTS covers full range)
    return points[-1][1]


def local_rank_for_pp_mode(pp: PP, game_mode: osuGameMode) -> RANK:
    # last updated: 3/22/2026
    STD_POINTS: list[tuple[PP, RANK]] = [
        (33_358, 1),
        (12_211, 2451),
        (10_749, 4951),
        (10_010, 7451),
        (9_444, 9951),
        (5133, 96478),
        (937, 918194),
        (0, 26_971_582),
    ]

    if game_mode == osuGameMode.STANDARD:
        return local_rank_for_pp(pp, STD_POINTS)
    else:
        warning_msg = f"Local rank estimation not available for game mode {game_mode}. Returning default rank 9999."
        log.warning(warning_msg)
        return 6767


async def rank_for_pp(pp: PP, game_mode: osuGameMode) -> RANK:
    """
    Fetch rank for given PP value using osu!daily API.

    Delegates to usecases.osu_daily.get_rank_for_pp which handles:
    - Credential validation
    - API communication
    - Error handling and client logout on auth failure

    Returns:
        Rank as integer (defaults to 9999 if fetch fails)
    """
    if pp < 700:  # osu!daily returns null for ranks below ~700pp
        # Linear interpolation for fetching this value
        return local_rank_for_pp_mode(pp, game_mode)

    rank = await usecases.osu_daily.get_rank_for_pp(pp, game_mode)

    if rank is not None:
        return rank

    # rank for osu!daily isn't working (could be due to missing/invalid credentials or API error)
    # retrive rough estimate using local interpolation of known PP->rank points
    log.warning(
        f"Falling back to local rank estimation for pp={pp} due to osu!daily API failure or missing credentials."
    )

    return local_rank_for_pp_mode(pp, game_mode)


Position = int
TotalScore = int


def position_for_score(
    scores_total_score: TotalScore, data_points: list[tuple[Position, TotalScore]]
) -> Position:
    if not data_points:
        raise ValueError("data_points cannot be empty")

    # Sort by total score (second element) to enable interpolation
    sorted_points = sorted(data_points, key=lambda p: p[1])

    # Extract sorted positions and scores
    positions = [p[0] for p in sorted_points]
    scores = [p[1] for p in sorted_points]

    # Handle out-of-range scores by clamping to endpoints
    if scores_total_score <= scores[0]:
        return positions[0]
    if scores_total_score >= scores[-1]:
        return positions[-1]

    # Find the interval containing the target score
    for i in range(len(scores) - 1):
        if scores[i] <= scores_total_score <= scores[i + 1]:
            # Linear interpolation
            x1, y1 = scores[i], positions[i]
            x2, y2 = scores[i + 1], positions[i + 1]
            # Avoid division by zero (should not happen if scores are distinct)
            if x2 == x1:
                return round((y1 + y2) / 2)
            position = y1 + (scores_total_score - x1) * (y2 - y1) / (x2 - x1)
            return round(position)

    # Should never reach here if the loop covers all cases
    raise RuntimeError("Unexpected error during interpolation")
