import aiohttp
import ossapi.models

import cache
import calculator
import usecases.osu_files
from adapters import OsuFile, log
from models.domain.gameplay import Mods, osuGameMode


@cache.retrive_osu_file_from_web.function
async def retrive_osu_file_from_web(beatmap_id: int) -> OsuFile | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://osu.ppy.sh/osu/{beatmap_id}") as response:
            if response.status != 200:
                log.warning(
                    f"Failed to retrieve .osu file for beatmap id {beatmap_id}, status code: {response.status}"
                )
                return None

            return OsuFile.from_raw(await response.content.read())


# When doing database changes, NEVER cache the functions that interact with the database,
# as it can lead to stale data being served. Always cache at the usecase level, where the data is
# processed and ready to be served to the client.
async def retrive_osu_file(
    beatmap_id: int,
    beatmap_md5: str | None = None,
) -> OsuFile | None:
    if beatmap_md5 is not None:
        osu_file = await usecases.osu_files.get_by_md5(beatmap_md5)

    if osu_file is not None:
        return osu_file

    osu_file = await retrive_osu_file_from_web(beatmap_id)

    if osu_file is not None:
        await usecases.osu_files.store(osu_file, store_audio=False)

    return osu_file


async def calc_pp_for_api_score(
    score: ossapi.models.Score,
    beatmap_id: int,
    game_mode: osuGameMode,
    beatmap_md5: str | None = None,
) -> int:
    osu_file = await retrive_osu_file(
        beatmap_id=beatmap_id,
        beatmap_md5=beatmap_md5,
    )

    if osu_file is None:
        log.warning(
            f"Could not retrieve .osu file for score {score.id}, cannot calculate pp"
        )
        return 0

    return calculator.pp(
        map_file=osu_file,
        game_mode=game_mode,
        mods=Mods.from_api_v2(score.mods),
        combo=score.max_combo,
        n300=score.statistics.great or 0,
        n100=score.statistics.ok or 0,
        n50=score.statistics.meh or 0,
        nmiss=score.statistics.miss or 0,
    )
