"""
Purpose/Domain/Concept:
- This file contains the logic related to user profiles.
"""

import usecases.domain.calculator.rank
# from adapters import log_time
from models.database.profiles import (
    CurrentProfile as Profile,
)
from models.database.profiles import (
    CurrentProfiles as Profiles,
)
from osu_protocol.osu.types import osuMapStatus
from osu_protocol.cho.server import osuGameMode
from repositories.beatmaps import BeatmapsRepository
from repositories.profiles import ProfilesRepository
from repositories.scores import ScoresRepository
import usecases.domain.cache_control


async def get_profiles() -> Profiles | None:
    profiles_repo = ProfilesRepository()
    return await profiles_repo.get_all()


@usecases.domain.cache_control.cache_profiles
async def get_profile(profile_name: str) -> Profile | None:
    profiles_repo = ProfilesRepository()
    return await profiles_repo.get(profile_name)


# log
async def create_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository()
    await profiles_repo.create_new_profile(profile_name)
    return


# log
async def delete_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository()
    await profiles_repo.delete_profile(profile_name)
    return


# log
async def update_profile(profile_name: str, updated_profile: Profile) -> None:
    profiles_repo = ProfilesRepository()
    await profiles_repo.update_profile(profile_name, updated_profile)
    return


async def remove_friend_from_profile(profile_name: str, friend_user_id: int) -> None:
    profiles_repo = ProfilesRepository()

    profile = await profiles_repo.get(profile_name)

    if profile is None:
        return

    if friend_user_id in profile.friend_ids:
        profile.friend_ids.remove(friend_user_id)
        await profiles_repo.update_profile(profile_name, profile)

    return

async def recalculate_stats(
    profile_name: str, game_mode: osuGameMode, score_submitted_combo: int | None = None
) -> Profile | None:
    profile_repo = ProfilesRepository()
    scores_repo = ScoresRepository()
    beatmaps_repo = BeatmapsRepository()

    profile = await profile_repo.get(profile_name)
    if profile is None:
        return None

    profile_stats = profile.performance[game_mode]

    # O(1) lookup: get all scores for this profile only
    profile_scores = await scores_repo.get_scores_for_profile(profile_name)

    if profile_scores is None:
        # No scores yet for this profile
        profile_stats.playcount += 1
        await profile_repo.update_profile(profile_name, profile)
        return profile

    best_scores_per_map = []
    total_score = 0
    ranked_score = 0

    # Gather all scores for this profile + mode.
    for map_scores in profile_scores.scores.values():
        mode_scores = []

        for score in map_scores.scores:
            if score.game_mode != game_mode:
                continue

            mode_scores.append(score)
            total_score += score.total_score

            # Only count ranked_score for maps that are RANKED, APPROVED, LOVED, or QUALIFIED
            beatmap = await beatmaps_repo.from_md5(score.beatmap_md5)
            if beatmap:
                bmap_status = beatmap.status[profile_name]
                if bmap_status in (
                    osuMapStatus.RANKED,
                    osuMapStatus.APPROVED,
                    osuMapStatus.LOVED,
                    osuMapStatus.QUALIFIED,
                ):
                    ranked_score += score.total_score

        if mode_scores:
            # Keep a single best score per beatmap for profile pp/acc weighting.
            best_for_map = max(
                mode_scores,
                key=lambda score: (
                    score.performance_points or 0,
                    score.total_score,
                    score.time_set,
                ),
            )
            best_scores_per_map.append(best_for_map)

    # Weighting for pp/acc is based on best plays only.
    pp_source_scores = [
        score for score in best_scores_per_map if (score.performance_points or 0) > 0
    ]

    pp_source_scores.sort(
        key=lambda score: (score.performance_points or 0, score.total_score),
        reverse=True,
    )

    score_count = len(pp_source_scores)
    if score_count:
        top_scores = pp_source_scores[:100]
        weights = [0.95**i for i, _ in enumerate(top_scores)]

        weighted_pp = sum(
            (score.performance_points or 0) * weight
            for score, weight in zip(top_scores, weights)
        )
        weighted_acc = sum(
            score.accuracy * weight for score, weight in zip(top_scores, weights)
        )
        weight_total = sum(weights)

        computed_accuracy = weighted_acc / weight_total if weight_total else 0.0
        profile_stats.accuracy = max(0.0, min(1.0, computed_accuracy))
    else:
        weighted_pp = 0.0
        profile_stats.accuracy = 0.0

    profile_stats.playcount += 1
    profile_stats.total_score = total_score
    profile_stats.ranked_score = ranked_score

    bonus_pp = 416.6667 * (1 - 0.9994**score_count) if score_count else 0.0
    profile_stats.performance_points = round(weighted_pp + bonus_pp)

    if score_submitted_combo and score_submitted_combo > profile_stats.max_combo:
        profile_stats.max_combo = score_submitted_combo

    profile_stats.rank = await usecases.domain.calculator.rank.rank_for_pp(
        profile_stats.performance_points,
        game_mode,
    )

    await profile_repo.update_profile(profile_name, profile)

    return profile


async def add_friend(profile_name: str, friend_user_id: int) -> Profile | None:
    profiles_repo = ProfilesRepository()

    profile = await profiles_repo.get(profile_name)
    if profile is None:
        return

    if friend_user_id not in profile.friend_ids:
        profile.friend_ids.append(friend_user_id)
        await profiles_repo.update_profile(profile_name, profile)

    return profile
