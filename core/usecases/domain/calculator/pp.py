import rosu_pp_py as rosu
from pathlib import Path
from core.models.domain.gameplay.mods import Mods
from core.models.domain.gameplay.game_mode import GameMode

def calculate(
    map_file: Path,
    game_mode: GameMode,
    mods: Mods,
    combo: int,
    n300: int,
    n100: int,
    n50: int,
    nmiss: int,
) -> int:
    print(f"[PP_CALC] Starting PP calculation")
    print(f"[PP_CALC] Map: {map_file}, Mode: {game_mode}, Mods: {mods}")
    print(f"[PP_CALC] Combo: {combo}, 300: {n300}, 100: {n100}, 50: {n50}, Miss: {nmiss}")
    
    rosu_map = rosu.Beatmap(content=map_file.read_bytes())
    print(f"[PP_CALC] Beatmap loaded, suspicious: {rosu_map.is_suspicious()}")
    
    if rosu_map.is_suspicious():
        return 0

    stable_mods = mods.to_stable_mods()

    rosu_map.convert(
        game_mode.to_rosu(),
        stable_mods,
    )

    kwargs = {
        "mods": stable_mods,
        "combo": combo,
        "n300": n300,
        "n100": n100,
        "n50": n50,
        "misses": nmiss,
    }

    if mods.custom_rate():
        kwargs["clock_rate"] = mods.rate()

    adjustments = mods.attribute_adjustments()

    if adjustments["ar"] is not None:
        kwargs["ar"] = adjustments["ar"]
        kwargs["ar_with_mods"] = True

    if adjustments["od"] is not None:
        kwargs["od"] = adjustments["od"]
        kwargs["od_with_mods"] = True

    if adjustments["hp"] is not None:
        kwargs["hp"] = adjustments["hp"]
        kwargs["hp_with_mods"] = True

    if adjustments["cs"] is not None:
        kwargs["cs"] = adjustments["cs"]
        kwargs["cs_with_mods"] = True

    calculator = rosu.Performance(**kwargs)

    result = calculator.calculate(rosu_map)
    pp_value = int(result.pp)
    
    print(f"[PP_CALC] Calculated PP: {pp_value}")
    print(f"[PP_CALC] Full result - PP: {result.pp}, Difficulty: {result}")

    return pp_value