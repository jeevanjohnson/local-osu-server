from datetime import datetime
from typing import Any, Callable, Coroutine, Literal, TypeVar

from fastapi import APIRouter, Depends, Header, Request, Response

from core.osu_protocol.cho.enums import osuAction
import core.osu_protocol.cho.server as cho_server
import core.osu_protocol.cho.client as cho_client
import server.dependencies as dependencies
from core.models.domain.gameplay import GameMode, Mods

from core.osu_protocol.cho.client import (
    ChangeAction,
    ClientPackets,
    FriendAdd,
    FriendRemove,
    LogOut,
    Packet,
    Packets,
    Ping,
    SendPrivateMessage,
    SendPublicMessage,
    UserStatsRequest,
)
from core.usecases.application.player import Player

bancho = APIRouter()

@bancho.post("/")
async def client_request_handler(
    user_agent: Literal["osu!"] = Header(...),
    player: Player | None = Depends(dependencies.player),
    login_response: cho_server.Packets | None = Depends(dependencies.login_response),
    incoming_packets: cho_client.Packets = Depends(dependencies.incoming_packets),
):
    if login_response is not None:
        return Response(
            content=login_response.build(), 
            headers={"cho-token": "welcome-to-los-2026"}
        )
    
    if player is None:
        return Response(
            content = cho_server.reset().build(),
        )

    for packet in incoming_packets:
        if packet.id not in PACKET_HANDLERS:
            continue

        await PACKET_HANDLERS[ClientPackets(packet.id)](packet, player)

    return Response(
        content=player.extract_outgoing_packets()
    )

PacketType = TypeVar("PacketType", bound=Packet)
PACKET_HANDLER = Callable[[PacketType, Player], Coroutine[Any, Any, None]]
PACKET_HANDLERS: dict[
    ClientPackets,
    PACKET_HANDLER,
] = {}


def register_packet_handler(packet_id: ClientPackets, packet_type: type[PacketType]):
    def inner(func: PACKET_HANDLER) -> PACKET_HANDLER:
        async def wrapper(
            packet: Packet, player: Player
        ) -> None:
            if not isinstance(packet, packet_type):
                return None

            return await func(packet, player)

        PACKET_HANDLERS[packet_id] = wrapper
        return func

    return inner


@register_packet_handler(ClientPackets.PING, packet_type=Ping)
async def handle_ping(
    packet: Ping, player: Player
) -> None:
    return

@register_packet_handler(ClientPackets.CHANGE_ACTION, packet_type=ChangeAction)
async def on_action_change(
    packet: ChangeAction, player: Player
) -> None:
    client_state = player.get_client_state()
    
    client_state.status = osuAction(packet.action.value)
    if client_state.status != osuAction.OsuDirect:
        client_state.direct_reference.cursor_string = None
    
    client_state.status_message = packet.info_text.value
    client_state.mods = Mods.from_stable_int(packet.current_mods.value)
    client_state.game_mode = GameMode(packet.current_game_mode.value)

    client_state.beatmap.md5 = packet.beatmap_md5.value
    client_state.beatmap.id = packet.beatmap_id.value

    performance = player.get_performance(client_state.game_mode)

    client_state.outgoing_packets += cho_server.PlayerStats(
        user_id=2,
        action=client_state.status,
        info_text=client_state.status_message,
        beatmap_md5=client_state.beatmap.md5,
        mods=client_state.mods.to_stable_mods_int(),
        game_mode=client_state.game_mode,
        beatmap_id=client_state.beatmap.id,
        ranked_score=performance.ranked_score,
        accuracy=performance.accuracy,
        play_count=performance.playcount,
        total_score=performance.total_score,
        rank=performance.rank,
        performance_points=performance.performance_points
    )

    player.update_client_state(client_state)

    return

@register_packet_handler(ClientPackets.LOGOUT, packet_type=LogOut)
async def on_logout(
    packet: LogOut, player: Player
) -> None:
    client_state = player.get_client_state()

    if datetime.now().timestamp() - client_state.in_game_at.timestamp() < 1:
        return

    client_state.in_game = False
    client_state.status = osuAction.Idle
    client_state.status_message = ""
    client_state.beatmap.md5 = ""
    client_state.beatmap.id = 0
    client_state.game_mode = GameMode.STANDARD
    client_state.mods = Mods()
    client_state.direct_reference.cursor_string = None

    player.update_client_state(client_state)

    return

@register_packet_handler(ClientPackets.USER_STATS_REQUEST, packet_type=UserStatsRequest)
async def on_user_stats_request(
    packet: UserStatsRequest, player: Player
) -> None:
    
    user_ids = packet.user_ids.value

    if 3 in user_ids:
        user_ids.remove(3)
    
    if 2 not in user_ids:
        user_ids.append(2)
    
    # TODO: implement stats for other users (friends)

@register_packet_handler(ClientPackets.FRIEND_REMOVE, packet_type=FriendRemove)
async def on_friend_remove(
    packet: FriendRemove, player: Player
) -> None:
    friend_id = packet.friend_user_id.value

    profile = player.get_profile()
    if friend_id in profile.friend_ids:
        profile.friend_ids.remove(friend_id)
        player.update_profile(profile)

    client_state = player.get_client_state()
    client_state.outgoing_packets += cho_server.UserFriendList(profile.friend_ids)
    player.update_client_state(client_state) # TODO: logout packet?

    return


@register_packet_handler(ClientPackets.FRIEND_ADD, packet_type=FriendAdd)
async def on_friend_add(
    packet: FriendAdd, player: Player
) -> None:
    client_state = player.get_client_state()

    client_state.outgoing_packets += cho_server.Notification(
        "Adding friends this way is not supported in LOS! ʕ•̫͡•ʔ\n"
        "Please refer to the interface for adding friends."
    )

    player.update_client_state(client_state)


@register_packet_handler(
    ClientPackets.SEND_PUBLIC_MESSAGE, packet_type=SendPublicMessage
)
async def on_send_public_message(
    packet: SendPublicMessage, player: Player
) -> None:
    # TODO: messages
    return


@register_packet_handler(
    ClientPackets.SEND_PRIVATE_MESSAGE, packet_type=SendPrivateMessage
)
async def on_send_private_message(
    packet: SendPrivateMessage, player: Player
) -> None:
    # TODO: messages
    return