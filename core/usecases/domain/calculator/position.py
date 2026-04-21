from core.usecases.adapters.statistics import LinearInterpolation

def get_leaderboard_position(
    sorting_value: int,
    leaderboard_scores: list[tuple[int, int]],  # points of (position, sorting_value),
    total_scores: int,
) -> int:
    lowest_position = (total_scores, 0)
    leaderboard_scores.append(lowest_position)
    positon = LinearInterpolation(leaderboard_scores)
    return int(positon.approximate(sorting_value))