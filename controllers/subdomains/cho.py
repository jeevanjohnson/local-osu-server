"""
Purpose/Domain/Concept:
- This file builds the routes related to c*.ppy.sh
"""

from datetime import datetime
from typing import Any, Callable, Coroutine, Literal, TypeVar

from fastapi import APIRouter, Header, Request, Response

import usecases.beatmaps
import usecases.cho
import usecases.gui
import usecases.profiles
import usecases.server_settings
import usecases.sessions
from adapters import log, log_time
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from osuProtocol.client_packets import (
    ChangeAction,
    ClientPackets,
    LogOut,
    Packet,
    Packets,
    Ping,
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

        if not await usecases.server_settings.osu_daily_credentials_exist():
            warning = (
                "osu!daily API credentials not found. Using local linear interpolation for calculating ranking, "
                "can be inaccurate due to little data. For best results, please set up your credentials through the GUI."
            )
        else:
                warning = None

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
            warning=warning,
        )

        session.osu_client.opened = True
        session.osu_client.logged_in_at = datetime.now()
        session.songs_folder = await usecases.sessions.retrieve_songs_folder()
        session.replays_folder = await usecases.sessions.retrieve_replays_folder()

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

        emergency_response: ServerPackets | ServerPacket | None = await PACKET_HANDLERS[
            ClientPackets(packet._id)
        ](packet)

        if emergency_response is not None:
            return Response(
                content=emergency_response.build(),
            )

    if not session.packet_queue:
        return Response(content=b"")

    response_packets = session.packet_queue

    await usecases.sessions.clear_packet_queue()

    return Response(content=response_packets)


PACKET_HANDLERS: dict[
    ClientPackets,
    Callable[[Packet], Coroutine[Any, Any, ServerPackets | ServerPacket | None]],
] = {}
PacketType = TypeVar("PacketType", bound=Packet)
PACKET_HANDLER = Callable[
    [PacketType], Coroutine[Any, Any, ServerPackets | ServerPacket | None]
]


def register_packet_handler(packet_id: ClientPackets, packet_type: type[PacketType]):
    def inner(func: PACKET_HANDLER) -> PACKET_HANDLER:
        async def wrapper(packet: Packet) -> ServerPackets | ServerPacket | None:
            if not isinstance(packet, packet_type):
                return None

            return await func(packet)

        PACKET_HANDLERS[packet_id] = wrapper
        return func

    return inner


@register_packet_handler(ClientPackets.PING, packet_type=Ping)
async def handle_ping(packet: Ping) -> ServerPackets | ServerPacket | None:
    return


@register_packet_handler(ClientPackets.CHANGE_ACTION, packet_type=ChangeAction)
@log_time
async def on_action_change(packet: ChangeAction) -> ServerPackets | ServerPacket | None:
    # This should be taken care of via the decorater to remove redundancy
    # and be passed in as a parameter along with the packet
    try:
        session = await usecases.sessions.require_current_session()
    except SessionNotFoundError:
        return SilentRelog

    try:
        profile = await usecases.profiles.require_profile(session.profile_name)
    except ProfileNotFoundError:
        return SilentRelog

    session.osu_client.status = osuAction(packet.action.value)
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

    packet_enqueue = ServerPackets()
    packet_enqueue += PlayerStats(
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

    session.packet_queue += packet_enqueue.build()
    await usecases.sessions.update_current_session(session)


@register_packet_handler(ClientPackets.LOGOUT, packet_type=LogOut)
@log_time
async def on_logout(packet: LogOut):
    try:
        session = await usecases.sessions.require_current_session()
    except SessionNotFoundError:
        return

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
