import asyncio

import usecases.adapters.ossapi
import usecases.application.client.state
import usecases.domain.bancho.scores
import usecases.domain.beatmaps
import usecases.domain.cache_control
import usecases.domain.scores
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
from models.database.profiles import CurrentProfile as Profile
from models.domain.gameplay import Mods, osuGameMode
from models.domain.scores import AcceptedScores, AllScores
from osu_protocol.osu.leaderboard import (
    LeaderboardWithScores,
)
from osu_protocol.osu.types import LeaderboardType
from usecases.domain.scores import ScoringAlgorithm

Position = int
TotalScore = int


UserIDs = int

NO_LEADERBOARD_LIMIT = 1000000


@usecases.domain.cache_control.cache_leaderboard
async def personal_scores_leaderboard(
    profile_name: str,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    scoring_algorithm: ScoringAlgorithm,
) -> LeaderboardWithScores:
    personal_scores = await usecases.domain.scores.get_scores_for_beatmap(
        beatmap=beatmap,
        profile_name=profile_name,
        game_mode=game_mode,
    )

    personal_scores.sort(scoring_algorithm)

    if personal_scores.scores:
        personal_best = personal_scores.scores[0]
    else:
        personal_best = None

    return LeaderboardWithScores(
        profile_name=profile_name,
        beatmap=beatmap,
        scores=AllScores(personal_scores.scores),
        personal_best=personal_best,
        scoring_algorithm=scoring_algorithm,
        difficulty_adjusted=beatmap.difficulty_adjusted,
        limit=NO_LEADERBOARD_LIMIT,
        accepted_scores=AcceptedScores.BOTH,
    )


@usecases.domain.cache_control.cache_leaderboard
async def friends_leaderboard(
    profile_name: str,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    friends: list[UserIDs],
    scoring_algorithm: ScoringAlgorithm,
) -> LeaderboardWithScores:

    api_client = await usecases.adapters.ossapi.get()
    if not api_client:
        raise ConnectionError("Failed to get API client for fetching friends' scores.")

    # Refresh play_count/pass_count if stale
    beatmap = await usecases.domain.beatmaps.ensure_counts_fresh(
        beatmap=beatmap,
        api_client=api_client,
    )

    friends_scores = await usecases.domain.bancho.scores.get_friends_scores_for_beatmap(
        api_client=api_client,
        beatmap=beatmap,
        game_mode=game_mode,
        accepted_scores=accepted_scores,
        friends_user_ids=friends,
        scoring_algorithm=scoring_algorithm,
    )

    if friends_scores.total != 0:
        await usecases.application.client.state.update_avaliable_stable_replay_ids_from_scores(
            friends_scores
        )

    personal_best = await usecases.domain.scores.personal_best_for_beatmap(
        beatmap=beatmap,
        profile_name=profile_name,
        game_mode=game_mode,
        scoring_algorithm=scoring_algorithm,
    )

    return LeaderboardWithScores(
        profile_name=profile_name,
        beatmap=beatmap,
        scores=AllScores(friends_scores.scores),
        personal_best=personal_best,
        scoring_algorithm=scoring_algorithm,
        difficulty_adjusted=beatmap.difficulty_adjusted,
        limit=NO_LEADERBOARD_LIMIT,
        accepted_scores=accepted_scores,
    )


@usecases.domain.cache_control.cache_leaderboard
async def selected_mods_leaderboard(
    profile_name: str,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    limit: int,
    mods: Mods,
    scoring_algorithm: ScoringAlgorithm,
) -> LeaderboardWithScores:
    for redundant_mod in ["RX", "AP", "SV2"]:
        if redundant_mod in mods:
            mods.remove(redundant_mod)

    api_client = await usecases.adapters.ossapi.get()
    if not api_client:
        raise ConnectionError(
            "Failed to get API client for fetching mod-specific scores."
        )

    # Refresh play_count/pass_count if stale
    beatmap = await usecases.domain.beatmaps.ensure_counts_fresh(
        beatmap=beatmap,
        api_client=api_client,
    )

    bancho, personal_best = await asyncio.gather(
        usecases.domain.bancho.scores.get_mod_specific_scores_for(
            api_client=api_client,
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            mods=mods,
            scoring_algorithm=scoring_algorithm,
        ),
        usecases.domain.scores.personal_best_for_beatmap(
            beatmap=beatmap,
            profile_name=profile_name,
            game_mode=game_mode,
            scoring_algorithm=scoring_algorithm,
            mods=mods,
        ),
    )
    if bancho.total != 0:
        await usecases.application.client.state.update_avaliable_stable_replay_ids_from_scores(
            bancho
        )

    return LeaderboardWithScores(
        profile_name=profile_name,
        beatmap=beatmap,
        scores=AllScores(bancho.all_scores),
        personal_best=personal_best,
        scoring_algorithm=scoring_algorithm,
        difficulty_adjusted=beatmap.difficulty_adjusted,
        limit=limit,
        accepted_scores=accepted_scores,
    )


@usecases.domain.cache_control.cache_leaderboard
async def global_leaderboard(
    profile_name: str,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    limit: int,
    scoring_algorithm: ScoringAlgorithm,
) -> LeaderboardWithScores:

    api_client = await usecases.adapters.ossapi.get()
    if not api_client:
        raise ConnectionError("Failed to get API client for fetching global scores.")

    # Refresh play_count/pass_count if stale
    beatmap = await usecases.domain.beatmaps.ensure_counts_fresh(
        beatmap=beatmap,
        api_client=api_client,
    )

    bancho, personal_best = await asyncio.gather(
        usecases.domain.bancho.scores.get_any_scores_for(
            api_client=api_client,
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            scoring_algorithm=scoring_algorithm,
        ),
        usecases.domain.scores.personal_best_for_beatmap(
            beatmap=beatmap,
            profile_name=profile_name,
            game_mode=game_mode,
            scoring_algorithm=scoring_algorithm,
        ),
    )

    print(
        f"DEBUG global_leaderboard() - fetched {len(bancho.scores)} scores from Bancho API"
    )

    if bancho.total != 0:
        await usecases.application.client.state.update_avaliable_stable_replay_ids_from_scores(
            bancho
        )

    return LeaderboardWithScores(
        profile_name=profile_name,
        beatmap=beatmap,
        scores=AllScores(bancho.all_scores),
        personal_best=personal_best,
        scoring_algorithm=scoring_algorithm,
        difficulty_adjusted=beatmap.difficulty_adjusted,
        limit=limit,
        accepted_scores=accepted_scores,
    )


@usecases.domain.cache_control.cache_leaderboard
async def from_request(
    beatmap: Beatmap,
    leaderboard_type: LeaderboardType,
    game_mode: osuGameMode,
    profile_name: str,
    mods: Mods | None,
    profile: Profile,
    accepted_scores: AcceptedScores,
) -> LeaderboardWithScores:
    if leaderboard_type == LeaderboardType.TOP:
        return await global_leaderboard(
            profile_name=profile_name,
            scoring_algorithm=profile.settings.scoring.algorithm,
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            limit=profile.settings.leaderboard.score_limit,
        )
    elif leaderboard_type == LeaderboardType.MODS:
        assert mods is not None, "Mods must be provided for MODS leaderboard type."
        return await selected_mods_leaderboard(
            profile_name=profile_name,
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            limit=profile.settings.leaderboard.score_limit,
            mods=mods,
            scoring_algorithm=profile.settings.scoring.algorithm,
        )
    elif leaderboard_type == LeaderboardType.FRIENDS:
        return await friends_leaderboard(
            profile_name=profile_name,
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            friends=profile.friend_ids,
            scoring_algorithm=profile.settings.scoring.algorithm,
        )
    elif leaderboard_type == LeaderboardType.COUNTRY:
        return await personal_scores_leaderboard(
            profile_name=profile_name,
            beatmap=beatmap,
            game_mode=game_mode,
            scoring_algorithm=profile.settings.scoring.algorithm,
        )
    else:
        raise ValueError(f"Unsupported leaderboard type: {leaderboard_type}")
