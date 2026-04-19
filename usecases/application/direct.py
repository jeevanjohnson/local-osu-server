import ossapi.enums
from ossapi import Cursor

import usecases.adapters.ossapi
import usecases.domain.direct
from core.osu_protocol.osu.direct import (
    DirectBeatmapSet,
    DirectSearchResult,
)


async def page(
    query: str,
    status_type: ossapi.enums.BeatmapsetSearchCategory,
    mode: ossapi.enums.BeatmapsetSearchMode,
) -> tuple[DirectSearchResult | None, str | None]:
    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return None, None

    try:
        search_results = await api_client.search_beatmapsets(
            query=query,
            mode=mode,
            category=status_type,
            cursor=Cursor(),
        )
    except Exception as e:
        if "`None`" in str(e):
            return None, None
        else:
            raise e

    beatmap_sets = [
        await usecases.domain.direct.transform_beatmapset_to_direct(beatmap_set)
        for beatmap_set in search_results.beatmapsets
    ]

    return DirectSearchResult(beatmap_sets=beatmap_sets), search_results.cursor_string


async def scheme(
    map_set_id: int | None = None,
    map_id: int | None = None,
) -> DirectBeatmapSet | None:
    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return None

    try:
        beatmap_set = await api_client.beatmapset(
            beatmapset_id=map_set_id,
            beatmap_id=map_id,
        )
    except Exception as e:
        if "`None`" in str(e):
            raise ValueError(
                "Failed to retrieve beatmap info during scheme request. "
                "Please notify a developer if you see this error."
            )
        else:
            raise e

    return await usecases.domain.direct.transform_beatmapset_to_direct(beatmap_set)
