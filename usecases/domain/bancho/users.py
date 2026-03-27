import asyncio
import inspect
from datetime import datetime
from typing import overload

import ossapi.models
from ossapi import ScoreType

import usecases.domain.calculator.bancho
from usecases.adapters.ossapiasync import OssapiAsync
from models.domain.gameplay import Mods
from osu_protocol.cho.server import (
    ALL_PRIVILEGES,
    Packets,
    PlayerPresence,
    PlayerStats,
    osuAction,
    osuCountryCode,
    osuGameMode,
)
from osu_protocol.cho.server import LogOut as PlayerLogOut


@overload
async def get(
    api_client: OssapiAsync,
    user_identifiers: int | str,
    game_mode: osuGameMode | None = None,
) -> ossapi.models.User | None: ...


@overload
async def get(
    api_client: OssapiAsync,
    user_identifiers: list[int],
    game_mode: osuGameMode | None = None,
) -> list[ossapi.models.UserCompact]: ...


# @cached_for_five_minutes
async def get(
    api_client: OssapiAsync,
    user_identifiers: list[int] | int | str,
    game_mode: osuGameMode | None = None,
) -> ossapi.models.User | list[ossapi.models.UserCompact] | None:

    if isinstance(user_identifiers, (int, str)):
        try:
            bancho_user = await api_client.user(
                user=user_identifiers, mode=game_mode.to_api_v2() if game_mode else None
            )
            print(
                f"Fetched user {bancho_user.username} (ID: {bancho_user.id}) from osu! API for user ID: {user_identifiers}"
            )
            return bancho_user
        except ValueError:
            print(f"User with identifier {user_identifiers} not found in osu! API.", )
            return None
    else:
        try:
            bancho_users = await api_client.users(user_ids=user_identifiers)
            print(
                f"Fetched {len(bancho_users)} users from osu! API for user IDs: {user_identifiers}"
            )
            return bancho_users
        except ValueError:
            print(f"Users with identifiers {user_identifiers} not found in osu! API.", )
            return []


# @cached_for_one_minute
def current_action(
    user: ossapi.models.UserCompact, recent_scores: list[ossapi.models.Score]
) -> osuAction:
    # linear regression or some statistic thing since we tryna find a general trend

    monthly_playcount_data: list[tuple[datetime, int]] = []

    if user.monthly_playcounts:
        for playcount in user.monthly_playcounts:
            monthly_playcount_data.append((playcount.start_date, playcount.count))

    score_times = [score.ended_at for score in recent_scores]

    print(
        f"Estimating player state for user {user.username} (ID: {user.id}) using monthly playcount data and recent score times."
    )

    probabilities, state = usecases.domain.calculator.bancho.estimate_player_state(
        monthly_playcount_data,
        score_times=score_times,  # type: ignore
    )

    print(
        f"Estimated player state for user {user.username} (ID: {user.id}): {state} with probabilities {probabilities}"
    )

    return state


async def get_presences_and_stats(
    api_client: OssapiAsync,
    user_ids: list[int],
    game_mode: osuGameMode,
) -> Packets:
    if not user_ids:
        print("No user IDs provided for fetching presences and stats.", )
        return Packets()

    bancho_friends = await get(api_client=api_client, user_identifiers=user_ids)

    print(
        f"User stats request includes {len(bancho_friends)} friends. Adding online friends' stats packets to response."
    )

    extended_users_tasks = [
        get(api_client=api_client, user_identifiers=friend.id, game_mode=game_mode)
        for friend in bancho_friends
    ]

    extended_users = await asyncio.gather(*extended_users_tasks)

    user_stats_map = {
        user.id: user
        for user in extended_users
        if user is not None and not isinstance(user, Exception)
    }

    recent_scores_tasks = [
        api_client.user_scores(
            user_id=friend.id,
            type=ScoreType.RECENT,
            include_fails=True,
            mode=game_mode.to_api_v2(),
        )
        for friend in bancho_friends
        if friend.is_online
    ]

    recent_scores_map = await asyncio.gather(*recent_scores_tasks)

    recent_scores: dict[int, list[ossapi.models.Score]] = {}

    for scores in recent_scores_map:
        if isinstance(scores, Exception):
            continue

        for score in scores:
            if score.beatmap is None:
                continue

            if score.beatmap.checksum is None:
                continue

            recent_scores[score.user_id] = scores
            break

    response = Packets()

    for friend in bancho_friends:
        if not friend.is_online:
            response += PlayerLogOut(friend.id)
            print(
                f"Friend {friend.username} (ID: {friend.id}) is offline. Skipping adding stats packet to response."
            )
            continue

        action = current_action(friend, recent_scores.get(friend.id, []))

        extended_user = user_stats_map.get(friend.id)

        if action != osuAction.Playing:
            info_text = ""
            beatmap_md5 = ""
            mods = Mods([])
            if extended_user:
                game_mode = osuGameMode.from_extended_user(extended_user.playmode)
            else:
                game_mode = osuGameMode.STANDARD
            beatmap_id = 0
        else:
            recent_score = recent_scores[friend.id][0]
            beatmap_set = recent_score.beatmap.beatmapset()  # type: ignore

            if inspect.iscoroutine(beatmap_set):
                beatmap_set = await beatmap_set  # type: ignore

            info_text = (
                f"{beatmap_set.artist} - {beatmap_set.title} [{recent_score.beatmap.version}] "  # type: ignore
                f"+{Mods.from_api_v2(recent_score.mods)}"
            )
            beatmap_md5 = recent_score.beatmap.checksum  # type: ignore
            mods = Mods.from_api_v2(recent_score.mods)
            game_mode = osuGameMode.from_api_v2(recent_score.beatmap.mode)  # type: ignore
            beatmap_id = recent_score.beatmap.id  # type: ignore

        if extended_user and extended_user.statistics:
            ranked_score = extended_user.statistics.ranked_score
            accuracy = extended_user.statistics.hit_accuracy
            play_count = extended_user.statistics.play_count
            total_score = extended_user.statistics.total_score
            rank = extended_user.statistics.global_rank or 0
            if extended_user.statistics.pp is not None:
                pp = int(extended_user.statistics.pp)
            else:
                pp = 0
        else:
            ranked_score = 0
            accuracy = 0.0
            play_count = 0
            total_score = 0
            rank = 0
            pp = 0

        response += PlayerPresence(
            user_id=friend.id,
            username=friend.username,
            utc_offset=0,  # osu! API does not provide UTC offset, so defaulting to 0
            country_code=osuCountryCode.from_str(friend.country_code),
            user_privileges=ALL_PRIVILEGES,
            game_mode=game_mode,
            longitude=0.0,
            latitude=0.0,
            rank=rank,
        )

        print(
            f"DEBUG friend stats for {friend.username} (ID: {friend.id}): accuracy={accuracy} (type: {type(accuracy).__name__}), pp={pp} (type: {type(pp).__name__}), rank={rank} (type: {type(rank).__name__})"
        )

        response += PlayerStats(
            user_id=friend.id,
            action=action,
            info_text=info_text,
            beatmap_md5=beatmap_md5,  # type: ignore
            mods=mods.to_stable_mods()[0],
            game_mode=game_mode,
            beatmap_id=beatmap_id,
            ranked_score=ranked_score,
            accuracy=accuracy,
            play_count=play_count,
            total_score=total_score,
            rank=rank,
            performance_points=pp,
        )

    return response
