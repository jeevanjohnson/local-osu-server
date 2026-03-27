import usecases.adapters.ossapi
import usecases.domain.beatmaps
import usecases.domain.osufile
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
import usecases.domain.cache_control


async def from_osu_scheme_request(
    profile_name: str,
    # map_set_id: int | None = None,
    map_id: int | None = None,
    map_md5: str | None = None,
) -> Beatmap | None:
    api_client = await usecases.adapters.ossapi.get()

    if api_client is None:
        return None

    if map_md5 is not None:
        beatmap = await usecases.domain.beatmaps.from_api_md5(
            api_client=api_client,
            beatmap_md5=map_md5,
            profile_name=profile_name,
        )
        if beatmap:
            return beatmap

    if map_id is not None:
        beatmap = await usecases.domain.beatmaps.from_api_id(
            api_client=api_client,
            beatmap_id=map_id,
            profile_name=profile_name,
        )
        if beatmap:
            return beatmap

    # if map_set_id is not None:
    #     return None

    return None

@usecases.domain.cache_control.cache_beatmaps
async def from_leaderboard_request(
    beatmap_md5: str,
    beatmap_set_id: int,
    map_filename: str,
    profile_name: str,
) -> Beatmap | None:

    beatmap = await usecases.domain.beatmaps.from_db(beatmap_md5)
    if beatmap:
        return beatmap

    api_client = await usecases.adapters.ossapi.get()

    if api_client is None:
        return None

    # Phase 2: Check for difficulty-adjusted BEFORE calling API
    # (so we use the original beatmap's custom status instead of Bancho's)
    if usecases.domain.osufile.valid_difficulty_adjusted_filename(map_filename):
        difficulty_adjusted_beatmap = (
            await usecases.domain.beatmaps.from_difficulty_adjusted_request(
                api_client=api_client,
                profile_name=profile_name,
                beatmap_md5=beatmap_md5,
                beatmap_set_id=beatmap_set_id,
                map_filename=map_filename,
            )
        )
        if difficulty_adjusted_beatmap is not None:
            return difficulty_adjusted_beatmap

    # Phase 3: API
    beatmap = await usecases.domain.beatmaps.from_api_md5(
        api_client=api_client,
        beatmap_md5=beatmap_md5,
        profile_name=profile_name,
        filename=map_filename,
    )
    if beatmap:
        return beatmap

    # Phase 4: Check for unsubmitted map
    unsubmitted_map = await usecases.domain.beatmaps.find_unsubmitted_map(
        profile_name=profile_name,
        beatmap_md5=beatmap_md5,
        beatmap_set_id=beatmap_set_id,
        map_filename=map_filename,
    )
    if unsubmitted_map is not None:
        return unsubmitted_map

    # Phase 5: Call the user to update the map
    return None

@usecases.domain.cache_control.cache_beatmaps
async def from_score_submission_request(
    beatmap_md5: str, profile_name: str
) -> Beatmap | None:
    beatmap = await usecases.domain.beatmaps.from_db(beatmap_md5)
    if beatmap:
        return beatmap

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return None

    beatmap = await usecases.domain.beatmaps.from_api_md5(
        api_client=api_client,
        beatmap_md5=beatmap_md5,
        profile_name=profile_name,
    )

    if beatmap:
        return beatmap

    return None


async def refresh_status_from_api(profile_name: str, beatmap: Beatmap) -> Beatmap:
    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return beatmap

    refreshed_beatmap = (
        await usecases.domain.beatmaps.refresh_beatmapset_status_from_api(
            api_client=api_client,
            beatmap=beatmap,
            profile_name=profile_name,
        )
    )

    if refreshed_beatmap is None:
        return beatmap

    return refreshed_beatmap

@usecases.domain.cache_control.cache_beatmaps
async def from_md5(beatmap_md5: str, profile_name: str) -> Beatmap | None:
    beatmap = await usecases.domain.beatmaps.from_db(beatmap_md5)
    if beatmap:
        return beatmap

    api_client = await usecases.adapters.ossapi.get()

    if api_client is None:
        return None

    # Phase 3: API
    beatmap = await usecases.domain.beatmaps.from_api_md5(
        api_client=api_client,
        beatmap_md5=beatmap_md5,
        profile_name=profile_name,
    )
    if beatmap:
        return beatmap
