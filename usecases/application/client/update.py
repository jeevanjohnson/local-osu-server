import usecases.adapters.ossapi
import usecases.domain.bancho.users
from models.database.client.state import ClientState
from models.database.profiles import CurrentProfile as Profile
from models.domain.gameplay import Mods
from osuProtocol.server_packets import (
    ClientRelog,
    LogOut,
    Message,
    Notification,
    PlayerPresence,
    PlayerStats,
    osuAction,
    osuCountryCode,
    osuGameMode,
)
from repositories.client.state import ClientStateRepository
from repositories.client.update import ClientUpdateRepository


async def clear() -> bytes:
    client_update_repo = ClientUpdateRepository()
    result = await client_update_repo.clear()
    print(f"Cleared {len(result)} bytes from packet queue")
    return result


async def stats_with_profile(profile: Profile) -> None:
    client_state_repo = ClientStateRepository()
    client_state = await client_state_repo.get_client_state()

    await stats_with_state_and_profile(
        client_state=client_state,
        profile=profile,
    )


async def stats_with_state_and_profile(
    client_state: ClientState,
    profile: Profile,
) -> None:
    ranked_score = profile.performance[client_state.game_mode].ranked_score
    accuracy = profile.performance[client_state.game_mode].accuracy
    play_count = profile.performance[client_state.game_mode].playcount
    total_score = profile.performance[client_state.game_mode].total_score
    rank = profile.performance[client_state.game_mode].rank
    performance_points = profile.performance[client_state.game_mode].performance_points

    print(
        f"DEBUG stats_with_state_and_profile: ranked_score={ranked_score}, accuracy={accuracy}, play_count={play_count}, total_score={total_score}, rank={rank}, pp={performance_points}"
    )

    await stats(
        status=client_state.status,
        status_message=client_state.status_message,
        beatmap_md5=client_state.beatmap.md5,
        mods=client_state.mods,
        game_mode=client_state.game_mode,
        beatmap_id=client_state.beatmap.id,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        rank=rank,
        performance_points=performance_points,
        user_id=2,
    )


async def stats(
    status: osuAction,
    status_message: str,
    beatmap_md5: str,
    mods: Mods,
    game_mode: osuGameMode,
    beatmap_id: int,
    ranked_score: int,
    accuracy: float,
    play_count: int,
    total_score: int,
    rank: int,
    performance_points: int,
    user_id: int,
) -> None:
    client_update_repo = ClientUpdateRepository()

    print(
        f"DEBUG stats() - Creating PlayerStats: user_id={user_id}, action={status}, info_text='{status_message}'"
    )
    print(f"DEBUG stats() - beatmap_md5='{beatmap_md5}', beatmap_id={beatmap_id}")
    print(f"DEBUG stats() - mods={mods}, game_mode={game_mode}")
    print(f"DEBUG stats() - scores - ranked={ranked_score}, total={total_score}")
    print(
        f"DEBUG stats() - accuracy={accuracy} (type: {type(accuracy).__name__}), play_count={play_count}"
    )
    print(
        f"DEBUG stats() - rank={rank} (type: {type(rank).__name__}), pp={performance_points} (type: {type(performance_points).__name__})"
    )

    player_stats = PlayerStats(
        user_id=user_id,
        action=status,
        info_text=status_message,
        beatmap_md5=beatmap_md5,
        mods=mods.to_stable_mods()[0],
        game_mode=game_mode,
        beatmap_id=beatmap_id,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        rank=rank,
        performance_points=performance_points,
    )
    print(f"DEBUG stats() - PlayerStats created successfully")
    print(
        f"Queuing PlayerStats packet: action={status.name}, status_msg='{status_message}', accuracy={accuracy}"
    )
    await client_update_repo.queue(player_stats)


async def presence(
    user_id: int,
    username: str,
    utc_offset: int,
    country_code: osuCountryCode,
    user_privileges: int,
    game_mode: osuGameMode,
    longitude: float,
    latitude: float,
    rank: int,
) -> None:
    client_update_repo = ClientUpdateRepository()
    await client_update_repo.queue(
        PlayerPresence(
            user_id=user_id,
            username=username,
            utc_offset=utc_offset,
            country_code=country_code,
            user_privileges=user_privileges,
            game_mode=game_mode,
            longitude=longitude,
            latitude=latitude,
            rank=rank,
        )
    )


async def stats_and_presence_for_bancho_bot(info_message: str = "enjoy :)") -> None:
    await presence(
        user_id=3,
        username="BanchoBot",
        utc_offset=0,
        country_code=osuCountryCode.US,
        user_privileges=0,
        game_mode=osuGameMode.STANDARD,
        longitude=0.0,
        latitude=0.0,
        rank=0,
    )

    await stats(
        status=osuAction.Idle,
        status_message=info_message,
        beatmap_md5="",
        mods=Mods(),
        game_mode=osuGameMode.STANDARD,
        beatmap_id=0,
        ranked_score=0,
        accuracy=0.0,
        play_count=0,
        total_score=0,
        rank=0,
        performance_points=0,
        user_id=3,
    )


async def stats_and_presence_for_player(
    client_state: ClientState, profile: Profile
) -> None:
    """Send both presence and stats for the player (user_id=2) in response to stats requests."""
    # Send presence first (required by protocol)
    await presence(
        user_id=2,
        username=client_state.profile_name,
        utc_offset=0,
        country_code=osuCountryCode.US,
        user_privileges=0,
        game_mode=client_state.game_mode,
        longitude=0.0,
        latitude=0.0,
        rank=profile.performance[client_state.game_mode].rank,
    )

    # Then send stats
    await stats_with_state_and_profile(client_state=client_state, profile=profile)


async def notify(message: str) -> None:
    client_update_repo = ClientUpdateRepository()
    await client_update_repo.queue(Notification(message))


async def restart_client(message: str | None = None) -> None:
    client_update_repo = ClientUpdateRepository()
    if message is not None:
        await client_update_repo.queue(Notification(message))

    await client_update_repo.queue(ClientRelog(millisecond_delay=0))


async def friend_remove(user_id: int) -> None:
    client_update_repo = ClientUpdateRepository()
    await client_update_repo.queue(LogOut(user_id))


async def friends(
    user_ids: list[int],
    game_mode: osuGameMode,
) -> None:
    client_update_repo = ClientUpdateRepository()

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        await restart_client()
        return

    friends_packets = await usecases.domain.bancho.users.get_presences_and_stats(
        api_client=api_client,
        user_ids=user_ids,
        game_mode=game_mode,
    )

    await client_update_repo.queue(friends_packets)


async def friend_add(user_id: int, game_mode: osuGameMode) -> None:
    client_update_repo = ClientUpdateRepository()

    api_client = await usecases.adapters.ossapi.get()
    if api_client is None:
        await restart_client()
        return

    friend_packets = await usecases.domain.bancho.users.get_presences_and_stats(
        api_client=api_client,
        user_ids=[user_id],
        game_mode=game_mode,
    )

    await client_update_repo.queue(friend_packets)


async def message(recipient: str, sender: str, message: str, sender_id: int) -> None:
    client_update_repo = ClientUpdateRepository()
    await client_update_repo.queue(
        Message(
            recipient=recipient, sender=sender, message=message, sender_id=sender_id
        )
    )


async def message_from_bancho_bot(recipient: str, msg: str) -> None:
    await message(recipient=recipient, sender="BanchoBot", message=msg, sender_id=3)
