from datetime import datetime
import inspect

from models.domain.gameplay import Mods, osuMods
from usecases.providers import get_ossapi_async
import ossapi.models
from osuProtocol.server_packets import BanchoUser, PlayerStats, osuGameMode, LogOut as PlayerLogOut
from cache import cached_for_five_minutes, cached_for_one_minute
from osuProtocol.server_packets import osuAction, Packets, PlayerPresence, osuCountryCode
import usecases.bancho_scores
import calculator.bancho
from typing import overload


@overload
async def get(user_ids: int, game_mode: osuGameMode | None = None) -> ossapi.models.User: ...

@overload
async def get(user_ids: list[int], game_mode: osuGameMode | None = None) -> list[ossapi.models.UserCompact]: ...

@cached_for_five_minutes
async def get(
    user_ids: list[int] | int,
    game_mode: osuGameMode | None = None
) -> ossapi.models.User | list[ossapi.models.UserCompact]:
    
    osuApi = await get_ossapi_async()

    if isinstance(user_ids, int):
        bancho_user = await osuApi.user(user=user_ids, mode=game_mode.to_api_v2() if game_mode else None)
        print(f"Fetched user {bancho_user.username} (ID: {bancho_user.id}) from osu! API for user ID: {user_ids}")
        return bancho_user
    else:
        bancho_users = await osuApi.users(user_ids=user_ids)
        print(f"Fetched {len(bancho_users)} users from osu! API for user IDs: {user_ids}")
        return bancho_users

@cached_for_one_minute
def current_action(user: ossapi.models.UserCompact, recent_scores: list[ossapi.models.Score]) -> osuAction:
    # linear regression or some statistic thing since we tryna find a general trend 
    
    monthly_playcount_data: list[tuple[datetime, int]] = []

    if user.monthly_playcounts:
        for playcount in user.monthly_playcounts:
            monthly_playcount_data.append((playcount.start_date, playcount.count))

    score_times = [score.ended_at for score in recent_scores]

    print(f"Estimating player state for user {user.username} (ID: {user.id}) using monthly playcount data and recent score times.")

    probabilities, state = calculator.bancho.estimate_player_state(
        monthly_playcount_data, 
        score_times=score_times  # type: ignore
    )

    print(f"Estimated player state for user {user.username} (ID: {user.id}): {state} with probabilities {probabilities}")

    return state

@cached_for_five_minutes
async def convert_to_osu_packets(
    user: ossapi.models.UserCompact,
    game_mode: osuGameMode,
    presence_aware: bool = False
) -> Packets:
    recent_scores = await usecases.bancho_scores.get_recent_from(
        user_id=user.id,
        game_mode=game_mode
    )
    action = current_action(user, recent_scores)

    if action != osuAction.Playing:
        info_text = ""
        beatmap_md5 = ""
        mods = Mods([])
        game_mode = osuGameMode.STANDARD
        beatmap_id = 0
    else:
        recent_score = recent_scores[0]

        beatmap_set = recent_score.beatmap.beatmapset() # type: ignore
        
        # If beatmapset() returns a coroutine, await it
        if inspect.iscoroutine(beatmap_set):
            beatmap_set = await beatmap_set # type: ignore

        assert beatmap_set is not None, "Beatmap set should not be None for a valid score"
        assert recent_score.beatmap is not None, "Beatmap should not be None for a valid score"
        assert recent_score.beatmap.checksum is not None, "Beatmap checksum should not be None for a valid score"

        info_text = f"{beatmap_set.artist} - {beatmap_set.title} [{recent_score.beatmap.version}] +{Mods.from_api_v2(recent_score.mods)}"
        beatmap_md5 = recent_score.beatmap.checksum
        mods = Mods.from_api_v2(recent_score.mods)
        game_mode = osuGameMode.from_api_v2(recent_score.beatmap.mode)
        beatmap_id = recent_score.beatmap.id
    
    extended_user = await get(user_ids=user.id, game_mode=game_mode)

    if extended_user.statistics:
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

    print(f"Converted user {user.username} (ID: {user.id}) to BanchoUser with action {action}, beatmap_md5 {beatmap_md5}, mods {mods}, game_mode {game_mode}, ranked_score {ranked_score}, accuracy {accuracy}, play_count {play_count}, total_score {total_score}, rank {rank}, pp {pp}")

    return BanchoUser(
        user_id=int(user.id),
        username=user.username,
        country_code=osuCountryCode.from_str(user.country_code),
        action=action,
        info_text=info_text,
        beatmap_md5=beatmap_md5,
        mods=mods.to_stable_mods()[0],
        game_mode=game_mode,
        beatmap_id=beatmap_id,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        rank=rank,
        performance_points=pp,
        presence_aware=presence_aware
    )

@cached_for_five_minutes
async def get_friends_client_status(
    user_ids: list[int],
    game_mode: osuGameMode,
    presence_aware: bool = False
) -> Packets:
    bancho_friends = await get(user_ids=user_ids)

    print(f"User stats request includes {len(bancho_friends)} friends. Adding online friends' stats packets to response.")

    response = Packets()
    for friend in bancho_friends:
        if not friend.is_online:
            response += PlayerLogOut(friend.id)
            print(f"Friend {friend.username} (ID: {friend.id}) is offline. Skipping adding stats packet to response.")
            continue

        print(f"Adding stats packet for online friend {friend.username} (ID: {friend.id}) to response.")
        response += await convert_to_osu_packets(friend, presence_aware=presence_aware, game_mode=game_mode)
    
    return response