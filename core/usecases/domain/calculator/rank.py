import core.usecases.domain.osu_scraper as osu_scraper_usecases
from core.usecases.adapters.statistics import PowerLawInterpolation
from core.models.domain.gameplay.game_mode import GameMode

def calculate_rank_for(pp: int, mode: GameMode) -> int:
    print(f"[RANK_CALC] Starting rank calculation for {pp}pp in {mode}")
    
    snapshot_result = osu_scraper_usecases.get_recent_snapshot()
    snapshot = snapshot_result["snapshot"]
    print(f"[RANK_CALC] Retrieved snapshot from {snapshot_result['timestamp']}")

    if mode == GameMode.STANDARD:
        points = snapshot.osu
        mode_name = "osu"
    elif mode == GameMode.TAIKO:
        points = snapshot.taiko
        mode_name = "taiko"
    elif mode == GameMode.CATCH:
        points = snapshot.catch
        mode_name = "catch"
    else:
        points = snapshot.mania
        mode_name = "mania"
    
    print(f"[RANK_CALC] Mode: {mode_name}, Points data available: {bool(points)}, Data points: {len(points) if points else 0}")
    
    if not points:
        print(f"[RANK_CALC] ❌ No points data available for rank calculation in {mode_name}. Returning rank 0")
        return 0

    print(f"[RANK_CALC] First point: {points[0]}, Last point: {points[-1]}")
    
    # Snapshot data is stored as (pp, rank) with anchor (0, total_players) at the end
    rank = PowerLawInterpolation(points)
    calculated_rank = int(rank.approximate(pp))
    
    print(f"[RANK_CALC] ✓ Calculated rank: #{calculated_rank} for {pp}pp")

    return calculated_rank