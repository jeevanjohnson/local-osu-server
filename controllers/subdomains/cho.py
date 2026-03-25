"""
Purpose/Domain/Concept:
- This file builds the routes related to c*.ppy.sh
"""

from datetime import datetime
from typing import Any, Callable, Coroutine, Literal, TypeVar

from fastapi import APIRouter, Header, Request, Response

import usecases.bancho_users
import usecases.cho
import usecases.gui
import usecases.latency
from models.database.sessions import (
    CurrentSession as Session,
)
import usecases.profiles
import usecases.server_settings
import usecases.sessions
import usecases.songs_folder
from cache import cached_forever
from adapters import log, log_time
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from osuProtocol.client_packets import (
    ChangeAction,
    ClientPackets,
    LogOut,
    Packet,
    Packets,
    Ping,
    UserStatsRequest,
    FriendRemove
)
from osuProtocol.server_packets import (
    Login,
    LoginAuthFailed,
    LoginError,
    PlayerStats,
    SilentRelog,
    osuAction,
    osuGameMode,
    osuMods,
    BanchoBot,
    LogOut as PlayerLogOut
)
from osuProtocol.server_packets import Packet as ServerPacket
from osuProtocol.server_packets import Packets as ServerPackets

bancho = APIRouter()


@bancho.post("/")
async def client_request_handler(
    request: Request,
    osu_token: str | None = Header(None),
    user_agent: Literal["osu!"] = Header(...),
):
    wants_login = osu_token is None

    if wants_login:
        if not await usecases.gui.logged_in():
            content = LoginAuthFailed(
                "You must be logged in through the GUI to use the osu! client."
            ).build()

            return Response(
                content=content,
                headers={"cho-token": "not-logged-in-gui"},
            )

        login_data = usecases.cho.parse_login_data(await request.body())

        try:
            session = await usecases.sessions.require_current_session()
        except SessionNotFoundError:
            content = LoginError(
                "No active session found. Please log in through the GUI."
            ).build()

            return Response(
                content=content,
                headers={"cho-token": "no-active-session"},
            )

        try:
            profile = await usecases.profiles.require_profile(session.profile_name)
        except ProfileNotFoundError:
            content = LoginError(
                "Profile not found. Please log in through the GUI."
            ).build()

            return Response(
                content=content,
                headers={"cho-token": "profile-not-found"},
            )

        if not await usecases.server_settings.credentials_exist():
            content = LoginError(
                "API v2 credentials not found. Please set up your credentials through the GUI and relog."
            ).build()

            return Response(
                content=content,
                headers={"cho-token": "api-v2-credentials-missing"},
            )

        login_message = f"Welcome to LOS!, {session.profile_name} ʕ•̫͡•ʔ"
        api_latency = await usecases.latency.bancho_api()
        login_message += f" \n(Bancho API latency: {api_latency:.2f}ms)"
        if not await usecases.server_settings.osu_daily_credentials_exist():
            login_message += "\n(Warning: osu!daily credentials not found. Using local ranking calc may result in inaccurate results)"

        rank = profile.performance[session.current_game_mode].rank
        ranked_score = profile.performance[session.current_game_mode].ranked_score
        accuracy = profile.performance[session.current_game_mode].accuracy
        play_count = profile.performance[session.current_game_mode].playcount
        total_score = profile.performance[session.current_game_mode].total_score
        performance_points = profile.performance[
            session.current_game_mode
        ].performance_points

        login_response = Login(
            username=session.profile_name,
            friend_ids=profile.friend_ids,
            utc_offset=login_data["utc_offset"],
            country_code=profile.country_code,
            game_mode=session.current_game_mode,
            longitude=0.0,
            latitude=0.0,
            rank=rank,
            ranked_score=ranked_score,
            accuracy=accuracy,
            play_count=play_count,
            total_score=total_score,
            performance_points=performance_points,
            login_message=login_message,
            latency=api_latency,
        )

        login_response += await usecases.bancho_users.get_friends_client_status(
            user_ids=profile.friend_ids,
            game_mode=session.current_game_mode,
            presence_aware=True
        )

        session.osu_client.opened = True
        session.osu_client.logged_in_at = datetime.now()

        await usecases.sessions.update_current_session(session)

        return Response(
            content=login_response.build(),
            headers={"cho-token": f"login-successful-for-{session.profile_name}"},
        )

    try:
        session = await usecases.sessions.require_current_session()
    except SessionNotFoundError:
        return Response(
            content=SilentRelog.build(),
        )

    incoming_packets = Packets(await request.body())
    incoming_packets.read()

    for packet in incoming_packets:
        if packet._id not in PACKET_HANDLERS:
            log.warning(
                f"Received packet with ID {ClientPackets(packet._id).name} but no handler is registered for this packet type."
            )
            continue

        response: ServerPackets | ServerPacket | None = await PACKET_HANDLERS[
            ClientPackets(packet._id)
        ](packet, session)

        if response is not None:
            session.packet_queue += response.build()

    print(f"Finished processing {len(incoming_packets)} incoming packets. Sending {len(session.packet_queue)} packets in response.")

    response_packets = session.packet_queue
    await usecases.sessions.clear_packet_queue()

    return Response(content=response_packets)


PacketType = TypeVar("PacketType", bound=Packet)
PACKET_HANDLER = Callable[
    [PacketType, Session], Coroutine[Any, Any, ServerPackets | ServerPacket | None]
]
PACKET_HANDLERS: dict[
    ClientPackets,
    PACKET_HANDLER,
] = {}

def register_packet_handler(packet_id: ClientPackets, packet_type: type[PacketType]):
    def inner(func: PACKET_HANDLER) -> PACKET_HANDLER:
        async def wrapper(packet: Packet, session: Session) -> ServerPackets | ServerPacket | None:
            if not isinstance(packet, packet_type):
                return None

            return await func(packet, session)

        PACKET_HANDLERS[packet_id] = wrapper
        return func

    return inner


@register_packet_handler(ClientPackets.PING, packet_type=Ping)
async def handle_ping(packet: Ping, session: Session) -> ServerPackets | ServerPacket | None:
    return


@register_packet_handler(ClientPackets.CHANGE_ACTION, packet_type=ChangeAction)
@log_time
async def on_action_change(packet: ChangeAction, session: Session) -> ServerPackets | ServerPacket | None:
    try:
        profile = await usecases.profiles.require_profile(session.profile_name)
    except ProfileNotFoundError:
        return SilentRelog

    session.osu_client.status = osuAction(packet.action.value)
    if session.osu_client.status != osuAction.OsuDirect:
        session.osu_client.direct_cursor_string = None

    session.osu_client.status_message = packet.info_text.value
    session.osu_client.opened = True

    session.current_game_mode = osuGameMode(packet.current_game_mode.value)

    session.latest_enabled_mods = osuMods(packet.current_mods.value)

    # Update beatmap info via lb req

    # will have to update readme cause of api key grabbing
    # also import score button would be epic

    ranked_score = profile.performance[session.current_game_mode].ranked_score
    accuracy = profile.performance[session.current_game_mode].accuracy
    play_count = profile.performance[session.current_game_mode].playcount
    total_score = profile.performance[session.current_game_mode].total_score
    rank = profile.performance[session.current_game_mode].rank
    performance_points = profile.performance[
        session.current_game_mode
    ].performance_points

    response = ServerPackets()
    response += PlayerStats(
        user_id=2,
        action=osuAction(packet.action.value),
        info_text=packet.info_text.value,
        beatmap_md5=packet.beatmap_md5.value,
        mods=osuMods(packet.current_mods.value),
        game_mode=osuGameMode(packet.current_game_mode.value),
        beatmap_id=packet.beatmap_id.value,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        rank=rank,
        performance_points=performance_points,
    )

    await usecases.sessions.update_current_session(session) # TODO: will this break?

    return response


@register_packet_handler(ClientPackets.LOGOUT, packet_type=LogOut)
@log_time
async def on_logout(packet: LogOut, session: Session) -> ServerPackets | ServerPacket | None:
    # osu! client logs out as soon as the user logs in
    # just ensure that this packet is a valid logout
    # 1+ s after login
    if datetime.now().timestamp() - session.osu_client.logged_in_at.timestamp() < 1:
        return

    # Keep the GUI-authenticated session alive; only mark the osu client as disconnected.
    session.osu_client.opened = False
    session.osu_client.status = osuAction.Idle
    session.osu_client.status_message = ""
    session.latest_beatmap = None
    session.latest_enabled_mods = osuMods.NOMOD
    session.packet_queue = b""

    await usecases.sessions.update_current_session(session)

@register_packet_handler(ClientPackets.USER_STATS_REQUEST, packet_type=UserStatsRequest)
@log_time
# @cached_forever
# @cache_
async def on_user_stats_request(packet: UserStatsRequest, session: Session) -> ServerPackets | ServerPacket | None:
    user_ids = packet.user_ids.value
    print(user_ids)

    response = ServerPackets()

    if 3 in user_ids: # BanchoBot
        # print("User stats request includes BanchoBot. Adding BanchoBot packet to response.")
        response += BanchoBot(
            latency= await usecases.latency.bancho_api()
        )
        user_ids.remove(3)
    
    if 2 in user_ids: # The user
        # print("User stats request includes the user themselves. Adding player stats packet to response.")
        await usecases.sessions.update_current_session(session)
        user_ids.remove(2)

    response += await usecases.bancho_users.get_friends_client_status(
        user_ids=user_ids, 
        game_mode=session.current_game_mode,
        presence_aware=True
    )
    
    return response

@register_packet_handler(ClientPackets.FRIEND_REMOVE, packet_type=FriendRemove)
@log_time
async def on_friend_remove(packet: FriendRemove, session: Session) -> ServerPackets | ServerPacket | None:
    friend_user_id = packet.friend_user_id.value
    print(f"Received friend remove packet for user ID {friend_user_id}. Removing from session's friend list if present.")

    if friend_user_id in (2, 3):
        print(f"Received friend remove packet for special user ID {friend_user_id} (the user themselves or BanchoBot). Ignoring.")
        return

    try:
        profile = await usecases.profiles.require_profile(session.profile_name)
    except ProfileNotFoundError:
        return SilentRelog
    
    if friend_user_id in profile.friend_ids:
        await usecases.profiles.remove_friend_from_profile(session.profile_name, friend_user_id)
        print(f"Removed user ID {friend_user_id} from profile's friend list.")
    
    # log out so we don't request information from them again
    return PlayerLogOut(friend_user_id)