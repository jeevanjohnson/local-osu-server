import rosu_pp_py as rosu

import usecases.domain.cache_control
from models.domain.gameplay import Mods, osuGameMode, osuMods

# from adapters import log, log_time
from usecases.adapters.osu_file import OsuFile

# Mapping from osuGameMode to rosu GameMode
ROSU_GAME_MODE_MAP: dict[osuGameMode, rosu.GameMode] = {
    osuGameMode.STANDARD: rosu.GameMode.Osu,
    osuGameMode.TAIKO: rosu.GameMode.Taiko,
    osuGameMode.CATCH_THE_BEAT: rosu.GameMode.Catch,
    osuGameMode.MANIA: rosu.GameMode.Mania,
}


@usecases.domain.cache_control.cache_group("performance")
def pp_for_acc(
    map_file: OsuFile,
    game_mode: osuGameMode,
    mods: Mods,
    accuracy: float,
    misses: int = 0,
    combo: int | None = None,
) -> int:
    """Assuming score is from stable."""
    assert map_file.raw_file is not None, (
        "Map file content is required for pp calculation"
    )

    if combo is None:
        combo = map_file.max_combo

    rosu_map = rosu.Beatmap(content=map_file.raw_file)

    if rosu_map.is_suspicious():
        # log.warning("Beatmap is marked as suspicious, pp calculation denied to 0")
        return 0

    stable_mods, lazer_mods = mods.to_stable_mods()

    if "NC" in mods:
        # Ensure DT is applied for safe calculation.
        stable_mods |= osuMods.DOUBLETIME

    rosu_map.convert(
        ROSU_GAME_MODE_MAP[game_mode],  # type: ignore # Convert osuGameMode to rosu GameMode
        stable_mods,  # type: ignore
    )

    calculator = rosu.Performance(
        mods=stable_mods,  # type: ignore
        accuracy=accuracy,
        combo=combo,
        misses=misses,
    )

    result = calculator.calculate(rosu_map)

    return int(result.pp)


@usecases.domain.cache_control.cache_group("performance")
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
    if "WU" in mods or "WD" in mods:
        # log.warning("Score has WU or WD mods, pp calculation denied to 0")
        return 0

    assert map_file.raw_file is not None, (
        "Map file content is required for pp calculation"
    )

    rosu_map = rosu.Beatmap(content=map_file.raw_file)

    if rosu_map.is_suspicious():
        # log.warning("Beatmap is marked as suspicious, pp calculation denied to 0")
        return 0

    stable_mods, lazer_mods = mods.to_stable_mods()

    if "NC" in mods:
        # Ensure DT is applied for safe calculation.
        stable_mods |= osuMods.DOUBLETIME

    rosu_map.convert(
        ROSU_GAME_MODE_MAP[game_mode],  # type: ignore # Convert osuGameMode to rosu GameMode
        stable_mods,  # type: ignore
    )

    kwargs = {
        "mods": stable_mods,
        "combo": combo,
        "n300": n300,
        "n100": n100,
        "n50": n50,
        "misses": nmiss,
    }

    if mods.lazer_rate:
        kwargs["clock_rate"] = mods.rate()

    if "DA" in mods:
        adjustments = mods.difficulty_adjustments()

        if adjustments["approach_rate"] is not None:
            kwargs["ar"] = adjustments["approach_rate"]
            kwargs["ar_with_mods"] = True

        if adjustments["overall_difficulty"] is not None:
            kwargs["od"] = adjustments["overall_difficulty"]
            kwargs["od_with_mods"] = True

        if adjustments["drain_rate"] is not None:
            kwargs["hp"] = adjustments["drain_rate"]
            kwargs["hp_with_mods"] = True

        if adjustments["cs_change"] is not None:
            kwargs["cs"] = adjustments["cs_change"]
            kwargs["cs_with_mods"] = True

    calculator = rosu.Performance(**kwargs)

    result = calculator.calculate(rosu_map)

    return int(result.pp)
