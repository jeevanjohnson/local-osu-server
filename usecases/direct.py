import ossapi.enums

import usecases.sessions
from models.domain.gameplay import osuGameMode
from osuProtocol.client_web import (
    DirectBeatmap,
    DirectBeatmapSet,
    DirectSearchResult,
)
from usecases.providers import get_ossapi_async


async def page(
    query: str,
    status_type: ossapi.enums.BeatmapsetSearchCategory,
    mode: ossapi.enums.BeatmapsetSearchMode,
) -> DirectSearchResult | None:
    session = await usecases.sessions.require_current_session()

    osu_api = await get_ossapi_async()

    # TODO: This search process should be
    # in usecases.beatmaps
    try:
        search_results = await osu_api.search_beatmapsets(
            query=query,
            mode=mode,
            category=status_type,
        )
    except Exception as e:
        if "`None`" in str(e):
            return None
        else:
            raise e

    session.osu_client.direct_cursor_string = search_results.cursor_string
    await usecases.sessions.update_current_session(session)

    beatmap_sets: list[DirectBeatmapSet] = []

    for beatmap_set in search_results.beatmapsets:
        direct_beatmaps: list[DirectBeatmap] = []
        if beatmap_set.beatmaps is None:
            continue

        for beatmap in beatmap_set.beatmaps:
            direct_beatmaps.append(
                DirectBeatmap(
                    star_rating=beatmap.difficulty_rating,
                    difficulty_name=beatmap.version,
                    cs=beatmap.cs,
                    od=beatmap.accuracy,
                    ar=beatmap.ar,
                    hp=beatmap.drain,
                    mode=osuGameMode.from_api_v2(beatmap.mode),
                )
            )

        beatmap_sets.append(
            DirectBeatmapSet(
                id=beatmap_set.id,
                artist=beatmap_set.artist,
                title=beatmap_set.title,
                creator=beatmap_set.creator,
                has_video=beatmap_set.video,
                has_story=beatmap_set.storyboard,
                last_updated=beatmap_set.last_updated,
                status=beatmap_set.ranked,
                maps=direct_beatmaps,
            )
        )

    return DirectSearchResult(beatmap_sets=beatmap_sets)


async def scheme(
    map_set_id: int | None = None,
    map_id: int | None = None,
    checksum: str | None = None,
) -> DirectBeatmapSet:
    osu_api = await get_ossapi_async()

    try:
        # TODO: support checksum search
        beatmap_set = await osu_api.beatmapset(
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

    direct_beatmaps: list[DirectBeatmap] = []
    if beatmap_set.beatmaps is not None:
        for beatmap in beatmap_set.beatmaps:
            direct_beatmaps.append(
                DirectBeatmap(
                    star_rating=beatmap.difficulty_rating,
                    difficulty_name=beatmap.version,
                    cs=beatmap.cs,
                    od=beatmap.accuracy,
                    ar=beatmap.ar,
                    hp=beatmap.drain,
                    mode=osuGameMode.from_api_v2(beatmap.mode),
                )
            )

    return DirectBeatmapSet(
        id=beatmap_set.id,
        artist=beatmap_set.artist,
        title=beatmap_set.title,
        creator=beatmap_set.creator,
        has_video=beatmap_set.video,
        has_story=beatmap_set.storyboard,
        last_updated=beatmap_set.last_updated,
        status=beatmap_set.ranked,
        maps=direct_beatmaps,
    )
