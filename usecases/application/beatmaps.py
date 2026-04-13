import usecases.adapters.ossapi
import usecases.domain.beatmaps
import usecases.domain.cache_control
import usecases.domain.osufile
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)


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
    print(
        f"[DEBUG] from_leaderboard_request: beatmap_md5={beatmap_md5}, beatmap_set_id={beatmap_set_id}, map_filename={map_filename}, profile_name={profile_name}"
    )

    # Check for difficulty-adjusted FIRST (before speed-modded detection)
    # This is important because difficulty-adjusted maps may contain speed syntax but aren't actually speed-modded
    is_difficulty_adjusted = usecases.domain.osufile.valid_difficulty_adjusted_filename(
        map_filename
    )
    print(
        f"[DEBUG] from_leaderboard_request: is_difficulty_adjusted={is_difficulty_adjusted} (checked first)"
    )

    # Detect if this is a speed-modded filename (but NOT if it's difficulty-adjusted)
    is_speed_modded = (
        usecases.domain.beatmaps.is_speed_modded_filename(map_filename)
        and not is_difficulty_adjusted
    )
    print(f"[DEBUG] from_leaderboard_request: is_speed_modded={is_speed_modded}")

    # Skip DB cache for invalid/modded versions (beatmap_set_id <= 0) because they may have old NOT_SUBMITTED entries
    # Also skip if it's a speed-modded filename AND DB returns NOT_SUBMITTED
    # Let them proceed to Phase 3b to resolve the original beatmap
    if beatmap_set_id > 0:
        beatmap = await usecases.domain.beatmaps.from_db(beatmap_md5)
        print(
            f"[DEBUG] from_leaderboard_request: from_db returned {'beatmap found' if beatmap else 'None'}"
        )

        # If speed-modded and we got NOT_SUBMITTED, treat as cache miss and go to Phase 3b
        if beatmap and is_speed_modded and beatmap.id == 0:
            print(
                f"[DEBUG] from_leaderboard_request: Found NOT_SUBMITTED entry for speed-modded filename, skipping to Phase 3b"
            )
            beatmap = None

        if beatmap:
            print(
                f"[DEBUG] from_leaderboard_request: returning beatmap from DB: id={beatmap.id}, status={beatmap.status}"
            )
            return beatmap
    else:
        print(
            f"[DEBUG] from_leaderboard_request: skipping DB cache lookup because beatmap_set_id={beatmap_set_id} (invalid/modded version)"
        )

    api_client = await usecases.adapters.ossapi.get()

    if api_client is None:
        print("[DEBUG] from_leaderboard_request: api_client is None")
        return None

    # Phase 2: Handle difficulty-adjusted maps
    print(
        f"[DEBUG] from_leaderboard_request: checking difficulty-adjusted (is_difficulty_adjusted={is_difficulty_adjusted}, map_filename={map_filename}"
    )
    if is_difficulty_adjusted and beatmap_set_id > 0:
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
            print(
                "[DEBUG] from_leaderboard_request: returning difficulty-adjusted beatmap"
            )
            return difficulty_adjusted_beatmap

    # Phase 3: API
    print(
        f"[DEBUG] from_leaderboard_request: calling from_api_md5 with beatmap_md5={beatmap_md5}"
    )
    beatmap = await usecases.domain.beatmaps.from_api_md5(
        api_client=api_client,
        beatmap_md5=beatmap_md5,
        profile_name=profile_name,
        filename=map_filename,
    )
    print(
        f"[DEBUG] from_leaderboard_request: from_api_md5 returned {'beatmap found' if beatmap else 'None'}"
    )
    if beatmap:
        print(
            f"[DEBUG] from_leaderboard_request: returning beatmap from API: id={beatmap.id}"
        )
        return beatmap

    # Phase 3b: If we have an invalid/modded version (beatmap_set_id <= 0) OR speed-modded filename and API lookup failed,
    # try to find the original beatmap by filename
    if beatmap_set_id <= 0 or is_speed_modded:
        if beatmap_set_id <= 0:
            print(
                f"[DEBUG] from_leaderboard_request: API failed for invalid/modded version (set_id={beatmap_set_id}), trying to find original beatmap from songs folder"
            )
        else:
            print(
                f"[DEBUG] from_leaderboard_request: API failed for speed-modded filename, trying to find original beatmap"
            )

        beatmap = await usecases.domain.beatmaps.from_local_file_by_filename(
            api_client=api_client,
            profile_name=profile_name,
            map_filename=map_filename,
        )
        if beatmap:
            print(
                f"[DEBUG] from_leaderboard_request: Found beatmap by local file resolution: {beatmap.id}"
            )
            # Delete any NOT_SUBMITTED entry for this speed-modded MD5 so it doesn't interfere later
            await usecases.domain.beatmaps.delete_not_submitted_entry_for_md5(
                beatmap_md5
            )
            return beatmap

    # Phase 4: Check for unsubmitted map
    # Skip unsubmitted check if beatmap_set_id is <= 0 (indicates invalid/modded version) or speed-modded filename
    if beatmap_set_id > 0 and not is_speed_modded:
        print(
            f"[DEBUG] from_leaderboard_request: checking for unsubmitted map (beatmap_set_id={beatmap_set_id})"
        )
        unsubmitted_map = await usecases.domain.beatmaps.find_unsubmitted_map(
            profile_name=profile_name,
            beatmap_md5=beatmap_md5,
            beatmap_set_id=beatmap_set_id,
            map_filename=map_filename,
        )
        if unsubmitted_map is not None:
            print(
                f"[DEBUG] from_leaderboard_request: returning unsubmitted beatmap: id={unsubmitted_map.id}, status={unsubmitted_map.status}"
            )
            return unsubmitted_map
    else:
        reason = (
            f"invalid/modded version"
            if beatmap_set_id <= 0
            else "speed-modded filename"
        )
        print(
            f"[DEBUG] from_leaderboard_request: skipping unsubmitted check because of {reason} (set_id={beatmap_set_id}, speed_modded={is_speed_modded})"
        )

    # Phase 5: Call the user to update the map
    print(f"[DEBUG] from_leaderboard_request: all phases failed, returning None")
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
