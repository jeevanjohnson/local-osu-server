import rosu_pp_py as rosu
from adapters import OsuFile
from models.domain.gameplay import Mods, osuGameMode, osuMods
from adapters.app_logger import app_logger

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