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
    if is_difficulty_adjusted:
        return "can't watch bancho plays on difficulty-adjusted maps"

    lazer_score = score_id not in available_replays
    if lazer_score:
        # Open in browser instead
        usecases.domain.replay.open_lazer_score(score_id=score_id)
        return "lazer score opened in browser"  # Special marker

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        return "failed to get api client for replay retrieval"

    replay_data = await usecases.domain.bancho.scores.get_replay(
        api_client=api_client,
        score_id=score_id,
        beatmap_md5=beatmap_md5,
    )

    if replay_data is None:
        return "replay data for this score is not available"

    return replay_data


async def get_local_replay(score_id: int) -> bytes | None:
    """Get replay for a local score."""
    score_id = abs(score_id)
    return await usecases.domain.scores.get_replay_frames_for_score_id(score_id)
