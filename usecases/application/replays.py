import usecases.adapters.ossapi
import usecases.application.client.update
import usecases.domain.bancho.scores
import usecases.domain.replay
import usecases.domain.scores


async def get_bancho_replay(
    score_id: int,
    beatmap_md5: str,
    is_difficulty_adjusted: bool,
    available_replays: list[int],
) -> bytes | str:
    """Get replay for a bancho score. Returns None if unavailable."""
    print(
        f"DEBUG get_bancho_replay: score_id={score_id}, beatmap_md5={beatmap_md5}, is_difficulty_adjusted={is_difficulty_adjusted}"
    )

    if is_difficulty_adjusted:
        return "can't watch bancho plays on difficulty-adjusted maps"

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "failed to get api client for replay retrieval"

    # Fetch the actual score data from the API to determine if it's a lazer score
    try:
        print(
            f"DEBUG get_bancho_replay: Fetching score data from API for score_id={score_id}"
        )
        score_data = await api_client.score(score_id=score_id)
        print(f"DEBUG get_bancho_replay: Score data fetched successfully")
    except Exception as e:
        print(
            f"ERROR get_bancho_replay: Exception fetching score data: {type(e).__name__}: {e}"
        )
        # Fall back to checking available_replays list if API fetch fails
        lazer_score = score_id not in available_replays
        if lazer_score:
            usecases.domain.replay.open_lazer_score(score_id=score_id)
            return "lazer score opened in browser"
        else:
            return "failed to fetch score data from API"

    # Check if it's a lazer score based on the actual score data
    is_lazer = usecases.domain.bancho.scores.api_is_score_lazer(score_data)
    print(f"DEBUG get_bancho_replay: is_lazer={is_lazer}")

    if is_lazer:
        # Open in browser instead
        print(f"DEBUG get_bancho_replay: Score is lazer, opening in browser")
        usecases.domain.replay.open_lazer_score(score_id=score_id)
        return "lazer score opened in browser"  # Special marker

    print(f"DEBUG get_bancho_replay: Score is stable, fetching replay data...")
    replay_data = await usecases.domain.bancho.scores.get_replay(
        api_client=api_client,
        score_id=score_id,
        beatmap_md5=beatmap_md5,
    )

    print(f"DEBUG get_bancho_replay: replay_data is None={replay_data is None}")

    if replay_data is None:
        return "replay data for this score is not available"

    return replay_data


async def get_local_replay(score_id: int) -> bytes | None:
    """Get replay for a local score."""
    score_id = abs(score_id)
    return await usecases.domain.scores.get_replay_frames_for_score_id(score_id)
