import functools

# use cause it takes a replay simulator to get an accurate scorev1, so this is good enough xd
@functools.cache
def estimate_scorev1(
    count_300: int,
    count_100: int, 
    count_50: int,
    score_max_combo: int, 
    mod_multiplier: float,
    hp: float, 
    cs: float,
    od: float, 
    beatmap_object_count: int,
    beatmap_drain_time_seconds: float,
    is_lazer: bool = False
) -> int:
    """
    Estimate ScoreV1 using only hit counts and max combo.

    Returns an integer score (rounded down, as in osu! stable).
    """

    density_bonus = (beatmap_object_count / beatmap_drain_time_seconds) * 8
    # Clamp the density bonus between 0 and 16
    clamped_bonus = max(0.0, min(16.0, density_bonus))

    # Sum all components
    total = hp + cs + od + clamped_bonus

    # Apply scaling and round to nearest integer
    multiplier = round((total / 38) * 5)
    difficulty_multiplier = int(multiplier)

    # List of all hit values, sorted descending
    hit_values = [300] * count_300 + [100] * count_100 + [50] * count_50
    total_non_miss = len(hit_values)

    # Hits that can be placed inside the max_combo streak
    streak_len = min(score_max_combo, total_non_miss)
    inside_streak = hit_values[:streak_len]          # highest values first
    outside_streak = hit_values[streak_len:]         # remaining hits

    total_score = 0

    # Score for hits inside the streak (combo grows from 0)
    for idx, value in enumerate(inside_streak):
        combo_before = idx
        multiplier = 1 + (combo_before * difficulty_multiplier * mod_multiplier / 25)
        total_score += value * multiplier

    # Score for hits outside the streak (combo = 0)
    for value in outside_streak:
        total_score += value  # multiplier = 1

    # Misses add nothing
    base_score = int(total_score)
    
    # DEBUG
    if "WU" in str(mod_multiplier) or "WD" in str(mod_multiplier) or mod_multiplier < 0.5:
        print(f"[SCORE DEBUG] base_score={base_score}, mod_multiplier={mod_multiplier}")
        print(f"[SCORE DEBUG]   hp={hp}, cs={cs}, od={od}, objects={beatmap_object_count}, drain={beatmap_drain_time_seconds}s")
        print(f"[SCORE DEBUG]   hits: {count_300}x300, {count_100}x100, {count_50}x50, combo={score_max_combo}")
    
    # Apply scaling based on score type:
    # - Stable (legacy): 6.0x to match Bancho reference values
    # - Lazer: 1.0x (no scaling - penalty for high mod multipliers)
    if base_score > 500000:
        if is_lazer:
            final_score = base_score  # Lazer: no scaling, raw base_score only
        else:
            final_score = int(base_score * 6.0)  # Stable scores get full boost
    else:
        final_score = base_score
    
    return final_score