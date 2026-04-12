from models.bancho.scores import Scores as BanchoScores
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
from models.database.scores import (
    CurrentMapScores as MapScores,
)
from models.database.scores import (
    CurrentScore as ProfileScore,
)
from models.domain.gameplay import Mods, osuGameMode
from models.domain.scores import (
    AllScores,
    ScoringAlgorithm,
)
from osu_protocol.domain.replay import extract_replay_frames_from_osr
from repositories.scores import ScoresRepository


async def generate_score_id() -> int:
    """Atomically allocate next score ID"""
    scores_repo = ScoresRepository()
    return await scores_repo.allocate_score_id()


async def get_scores_for_beatmap_from(
    beatmap_md5: str, profile_name: str | None = None
) -> MapScores:
    """Get scores for beatmap. If profile_name provided, get only that profile's scores."""
    scores_repo = ScoresRepository()

    if profile_name:
        map_scores = await scores_repo.get_scores_by_profile_and_beatmap_md5(
            profile_name, beatmap_md5
        )
    else:
        map_scores = await scores_repo.get_leaderboard_for_beatmap(beatmap_md5)

    return map_scores


async def get_scores_for_beatmap(
    beatmap: Beatmap,
    profile_name: str | None = None,
    game_mode: osuGameMode | None = None,
) -> MapScores:
    """Get scores for beatmap. If profile_name provided, get only that profile's scores."""
    map_scores = await get_scores_for_beatmap_from(beatmap.md5, profile_name)

    if game_mode is not None:
        map_scores = map_scores.filter_by(game_mode=game_mode)

    return map_scores


# log
async def score_rank(
    profile_score: ProfileScore,
    bancho_scores: BanchoScores,
    beatmap: Beatmap,
    scoring_algorithm: ScoringAlgorithm,
    leaderboard_limit: int,
) -> int:
    # bancho_scores = await usecases.domain.scores.get_scores_for_beatmap(
    #     profile_name=profile_score.username,
    #     beatmap=beatmap,
    #     game_mode=profile_score.game_mode,
    # )

    if not bancho_scores.scores:
        return 1

    all_scores = AllScores()
    all_scores.extend(bancho_scores.scores)
    all_scores.append(profile_score)

    return all_scores.position_of_score(
        profile_score,
        scoring_algorithm,
        beatmap_pass_count=beatmap.pass_count,
        leaderboard_limit=leaderboard_limit,
    )


# log
async def previous_best_score(
    beatmap: Beatmap,
    new_score: ProfileScore,
    scoring_algorithm: ScoringAlgorithm,
) -> ProfileScore | None:
    """Get the previous best score for this user on this beatmap.

    This is called after submission, so the repository can already contain
    new_score. We must exclude it, otherwise the first-ever play is treated as
    if it had a previous score.
    """
    map_scores = await get_scores_for_beatmap(
        beatmap=beatmap,
        profile_name=new_score.username,
        game_mode=new_score.game_mode,
    )

    if not map_scores.scores:
        return None

    existing_scores = [score for score in map_scores.scores if score.id != new_score.id]
    if not existing_scores:
        return None

    temp_map = MapScores(beatmap_md5=beatmap.md5, scores=existing_scores)
    temp_map.sort(scoring_algorithm)
    return temp_map.scores[0]


# log
async def personal_best_for_beatmap(
    beatmap: Beatmap,
    profile_name: str,
    game_mode: osuGameMode,
    scoring_algorithm: ScoringAlgorithm,
    mods: Mods | None = None,
) -> ProfileScore | None:
    """Get the personal best score for a beatmap and profile."""
    scores_repo = ScoresRepository()

    map_scores = await scores_repo.get_scores_by_profile_and_beatmap_md5(
        profile_name, beatmap.md5
    )

    if not map_scores:
        return None

    filtered_scores = map_scores.filter_by(
        game_mode=game_mode,
        mods=mods,
    )

    if not filtered_scores:
        return None

    if not filtered_scores.scores:
        return None

    filtered_scores.sort(scoring_algorithm)

    return filtered_scores.scores[0]


async def get_score_from_id(score_id: int) -> ProfileScore | None:
    """Get a score by its ID."""
    scores_repo = ScoresRepository()
    return await scores_repo.get_score_by_id(score_id)


# log
# @cached_forever
async def get_replay_frames_for_score_id(score_id: int) -> bytes | None:
    """Get replay frames for a given score ID, if available."""
    scores_repo = ScoresRepository()

    score = await scores_repo.get_score_by_id(
        score_id
    )  # Ensure score exists; raises if not found

    if score is None:
        return None

    if score.replay_frames is None:
        return None

    try:
        return extract_replay_frames_from_osr(score.replay_frames)[0]
    except Exception:
        # Already in form?
        return score.replay_frames


async def delete(score_id: int) -> None:
    """Delete a score by ID."""
    scores_repo = ScoresRepository()
    await scores_repo.delete_score_by_id(score_id)
