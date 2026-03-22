import rosu_pp_py as rosu
from adapters import OsuFile
from models.domain.gameplay import Mods, osuGameMode, osuMods
from adapters.app_logger import app_logger
import usecases.osu_daily

# Mapping from osuGameMode to rosu GameMode
ROSU_GAME_MODE_MAP: dict[osuGameMode, rosu.GameMode] = {
    osuGameMode.STANDARD: rosu.GameMode.Osu,
    osuGameMode.TAIKO: rosu.GameMode.Taiko,
    osuGameMode.CATCH_THE_BEAT: rosu.GameMode.Catch,
    osuGameMode.MANIA: rosu.GameMode.Mania,
}

@app_logger.log(msg="pp calculation started")
def pp(
        map_file: OsuFile,
        game_mode: osuGameMode,
        mods: Mods,
        combo: int,
        n300: int,
        n100: int,
        n50: int,
        nmiss: int,
) -> int:
    assert map_file.raw_file is not None, "Map file content is required for pp calculation"

    rosu_map = rosu.Beatmap(
        content=map_file.raw_file
    )

    if rosu_map.is_suspicious():
        app_logger.warning("Beatmap is marked as suspicious, pp calculation denied to 0")
        return 0

    stable_mods, lazer_mods = mods.to_stable_mods()

    if "NC" in mods:
        # Ensure DT is applied for safe calculation.
        stable_mods |= osuMods.DOUBLETIME

    rosu_map.convert(
        ROSU_GAME_MODE_MAP[game_mode],  # type: ignore # Convert osuGameMode to rosu GameMode
        stable_mods, # type: ignore 
    )

    calculator = rosu.Performance(
        mods=stable_mods,
        combo=combo,
        # acc=score.acc,
        n300=n300,
        n100=n100,
        n50=n50,
        # n_geki=score.ngeki,
        # n_katu=score.nkatu,
        misses=nmiss,
    )

    result = calculator.calculate(rosu_map)

    return int(result.pp)

PP = int
RANK = int
POINTS: list[tuple[PP, RANK]] = [
    (33_358, 1),
    (12_211, 2451),
    (10_749, 4951),
    (10_010, 7451),
    (9_444, 9951),
    (5133, 96478),
    (937, 918194),
    (0, 26_971_582),
]

# Linear interpolation
def local_rank_for_pp(pp: PP) -> RANK:
    """
    Estimate rank for given PP using linear interpolation of known points.
    
    Args:
        pp: Performance points value
        
    Returns:
        Estimated rank (as integer)
    """
    # Handle edge cases
    if pp >= POINTS[0][0]:
        return POINTS[0][1]
    if pp <= POINTS[-1][0]:
        return POINTS[-1][1]
    
    # Find the two points that bracket pp and interpolate
    for i in range(len(POINTS) - 1):
        pp1, rank1 = POINTS[i]
        pp2, rank2 = POINTS[i + 1]
        
        if pp2 <= pp <= pp1:
            t = (pp1 - pp) / (pp1 - pp2)  # t=0 at pp1, t=1 at pp2
            rank = rank1 + t * (rank2 - rank1)
            return int(round(rank))
    
    # Fallback to highest rank (shouldn't reach here if POINTS covers full range)
    return POINTS[-1][1]


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
    if pp < 700: # osu!daily returns null for ranks below ~700pp
        # Linear interpolation for fetching this value
        return local_rank_for_pp(pp)

    rank = await usecases.osu_daily.get_rank_for_pp(pp, game_mode)

    if rank is not None:
        return rank
    
    # rank for osu!daily isn't working (could be due to missing/invalid credentials or API error)
    # retrive rough estimate using local interpolation of known PP->rank points
    app_logger.warning(f"Falling back to local rank estimation for pp={pp} due to osu!daily API failure or missing credentials.")

    return local_rank_for_pp(pp)