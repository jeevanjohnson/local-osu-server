"""
Purpose/Domain/Concept:
- This file builds the routes related to c*.ppy.sh
"""

from datetime import datetime
from typing import Any, Callable, Coroutine, Literal, TypeVar

from fastapi import APIRouter, Header, Request, Response

import osuProtocol.server_packets
import usecases.bancho
import usecases.beatmaps
import usecases.gui
import usecases.profiles
import usecases.sessions
from osuProtocol.client_packets import (
    ChangeAction,
    ClientPackets,
    LogOut,
    Packet,
    Packets,
    Ping,
)
from osuProtocol.server_packets import (
    PlayerStats,
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
        if not usecases.gui.logged_in():
            failed_login_response = osuProtocol.server_packets.failed_login_response(
                "You must be logged in through the GUI to use the osu! client."
            )

            return Response(
                content=failed_login_response.build(),
                headers={"cho-token": "not-logged-in-gui"},
            )

        login_data = usecases.bancho.parse_login_data(await request.body())

        session = usecases.sessions.get_current_session()
        if session is None:
            failed_login_response = osuProtocol.server_packets.failed_login_response(
                "No active session found. Please log in through the GUI."
            )

            return Response(
                content=failed_login_response.build(),
                headers={"cho-token": "no-active-session"},
            )

        profile = usecases.profiles.get_profile(session.profile_name)

        if profile is None:
            failed_login_response = osuProtocol.server_packets.failed_login_response(
                "Profile not found. Please log in through the GUI."
            )

            return Response(
                content=failed_login_response.build(),
                headers={"cho-token": "profile-not-found"},
            )

        rank = profile.performance[session.current_game_mode].rank
        ranked_score = profile.performance[session.current_game_mode].ranked_score
        accuracy = profile.performance[session.current_game_mode].accuracy
        play_count = profile.performance[session.current_game_mode].playcount
        total_score = profile.performance[session.current_game_mode].total_score
        performance_points = profile.performance[
            session.current_game_mode
        ].performance_points

        successful_login_response = (
            osuProtocol.server_packets.successful_login_response(
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
            )
        )

        session.osu_client.opened = True
        session.osu_client.logged_in_at = datetime.now()
        session.songs_folder = usecases.sessions.retrieve_songs_folder()
        session.replays_folder = usecases.sessions.retrieve_replays_folder()

        usecases.sessions.update_current_session(session)

        return Response(
            content=successful_login_response.build(),
            headers={"cho-token": f"login-successful-for-{session.profile_name}"},
        )

    session = usecases.sessions.get_current_session()
    if session is None:
        return Response(
            content=osuProtocol.server_packets.client_relog_response().build(),
        )

    incoming_packets = Packets(await request.body())
    incoming_packets.read()

    for packet in incoming_packets:
        if packet._id not in PACKET_HANDLERS:
            print(
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

    usecases.sessions.clear_packet_queue()

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
async def on_action_change(packet: ChangeAction) -> ServerPackets | ServerPacket | None:
    session = usecases.sessions.get_current_session()
    if session is None:
        return osuProtocol.server_packets.client_relog_response()

    profile = usecases.profiles.get_profile(session.profile_name)
    if profile is None:
        return osuProtocol.server_packets.client_relog_response()

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
    usecases.sessions.update_current_session(session)

    # TODO: Handle this error case?
    # if updated_session is None:
    #     return osuProtocol.server_packets.client_relog_response()


@register_packet_handler(ClientPackets.LOGOUT, packet_type=LogOut)
async def on_logout(packet: LogOut):
    session = usecases.sessions.get_current_session()
    if session is None:
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

    usecases.sessions.update_current_session(session)
