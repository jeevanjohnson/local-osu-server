import ossapi.models

import calculator.performance
from adapters.osu_file import OsuFile
from models.domain.gameplay import Mods, osuGameMode


async def calc_pp_for_api_score(
    score: ossapi.models.Score,
    game_mode: osuGameMode,
    osu_file: OsuFile,
) -> int:
    return calculator.performance.pp(
        map_file=osu_file,
        game_mode=game_mode,
        mods=Mods.from_api_v2(score.mods),
        combo=score.max_combo,
        n300=score.statistics.great or 0,
        n100=score.statistics.ok or 0,
        n50=score.statistics.meh or 0,
        nmiss=score.statistics.miss or 0,
    )
