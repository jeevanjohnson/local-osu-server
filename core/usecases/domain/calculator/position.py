from core.usecases.adapters.statistics import LinearInterpolation

def get_leaderboard_position(
    sorting_value: int,
    leaderboard_scores: list[tuple[int, int]],  # points of (position, sorting_value),
    total_scores: int,
) -> int:
    print(f"[POS_CALC] Starting position calculation")
    print(f"[POS_CALC] Sorting value: {sorting_value}, Total scores: {total_scores}")
    print(f"[POS_CALC] Leaderboard scores (first 5): {leaderboard_scores[:5]}")
    
    # Anchor: a score of 0 gets position = total_scores
    lowest_position = (0, total_scores)
    leaderboard_scores.append(lowest_position)
    
    print(f"[POS_CALC] Added anchor point: {lowest_position}")
    print(f"[POS_CALC] Full leaderboard with anchor (last 3): {leaderboard_scores[-3:]}")
    
    positon = LinearInterpolation(leaderboard_scores)
    result = int(positon.approximate(sorting_value))
    
    print(f"[POS_CALC] ✓ Calculated position: #{result}")
    return result