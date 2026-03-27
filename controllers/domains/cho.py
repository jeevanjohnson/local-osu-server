"""
Purpose/Domain/Concept:
- This file builds the routes related to c*.ppy.sh
"""

from typing import Any, Callable, Coroutine, Literal, TypeVar

from fastapi import APIRouter, Depends, Header, Request, Response

import services.cho
import usecases.application.client.update
import usecases.cho
import usecases.domain.bancho.users
import usecases.domain.chats
import usecases.interface
from adapters import log, log_time
from controllers.dependencies import client_state, profile
from models.database.client.state import ClientState
from models.database.profiles import CurrentProfile as Profile
from osuProtocol.client_packets import (
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
from osuProtocol.server_packets import (
    SilentRelog,
)

bancho = APIRouter()


@bancho.post("/")
async def client_request_handler(
    request: Request,
    osu_token: str | None = Header(None),
    user_agent: Literal["osu!"] = Header(...),
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    wants_login = osu_token is None

    if wants_login:
        login_response = await services.cho.login(
            client_state=client_state, raw_login_data=await request.body()
        )

        return Response(
            content=login_response["client_response"],
            headers={"cho-token": login_response["status"]},
        )

    if profile is None:
        return Response(SilentRelog.build())

    incoming_packets = Packets(await request.body())
    incoming_packets.read()

    for packet in incoming_packets:
        if packet._id not in PACKET_HANDLERS:
            log.warning(
                f"Received packet with ID {ClientPackets(packet._id).name} but no handler is registered for this packet type."
            )
            continue

        await PACKET_HANDLERS[ClientPackets(packet._id)](packet, client_state, profile)

    response = await usecases.application.client.update.clear()

    return Response(content=response)


PacketType = TypeVar("PacketType", bound=Packet)
PACKET_HANDLER = Callable[[PacketType, ClientState, Profile], Coroutine[Any, Any, None]]
PACKET_HANDLERS: dict[
    ClientPackets,
    PACKET_HANDLER,
] = {}


def register_packet_handler(packet_id: ClientPackets, packet_type: type[PacketType]):
    def inner(func: PACKET_HANDLER) -> PACKET_HANDLER:
        async def wrapper(
            packet: Packet, client_state: ClientState, profile: Profile
        ) -> None:
            if not isinstance(packet, packet_type):
                return None

            return await func(packet, client_state, profile)

        PACKET_HANDLERS[packet_id] = wrapper
        return func

    return inner


@register_packet_handler(ClientPackets.PING, packet_type=Ping)
async def handle_ping(
    packet: Ping, client_state: ClientState, profile: Profile
) -> None:
    return


@register_packet_handler(ClientPackets.CHANGE_ACTION, packet_type=ChangeAction)
@log_time
async def on_action_change(
    packet: ChangeAction, client_state: ClientState, profile: Profile
) -> None:
    await services.cho.process_action_change(
        packet=packet, client_state=client_state, profile=profile
    )

    return


@register_packet_handler(ClientPackets.LOGOUT, packet_type=LogOut)
@log_time
async def on_logout(
    packet: LogOut, client_state: ClientState, profile: Profile
) -> None:
    await services.cho.process_logout(client_state=client_state, profile=profile)

    return


@register_packet_handler(ClientPackets.USER_STATS_REQUEST, packet_type=UserStatsRequest)
async def on_user_stats_request(
    packet: UserStatsRequest, client_state: ClientState, profile: Profile
) -> None:
    await services.cho.process_user_stats_request(
        user_ids=packet.user_ids.value, client_state=client_state, profile=profile
    )

    return


@register_packet_handler(ClientPackets.FRIEND_REMOVE, packet_type=FriendRemove)
@log_time
async def on_friend_remove(
    packet: FriendRemove, client_state: ClientState, profile: Profile
) -> None:
    await services.cho.process_friend_remove(
        friend_user_id=packet.friend_user_id.value,
        client_state=client_state,
        profile=profile,
    )
    return


@register_packet_handler(ClientPackets.FRIEND_ADD, packet_type=FriendAdd)
@log_time
async def on_friend_add(
    packet: FriendAdd, client_state: ClientState, profile: Profile
) -> None:
    await usecases.application.client.update.notify(
        "Adding friends through the client is not supported. "
        "Please add friends through the Interface or !add command."
    )


@register_packet_handler(
    ClientPackets.SEND_PUBLIC_MESSAGE, packet_type=SendPublicMessage
)
@log_time
async def on_send_public_message(
    packet: SendPublicMessage, client_state: ClientState, profile: Profile
) -> None:
    await services.cho.process_message(
        client_state=client_state,
        profile=profile,
        text=packet.text.value,
        recipient=packet.reciever.value,
    )
    return


@register_packet_handler(
    ClientPackets.SEND_PRIVATE_MESSAGE, packet_type=SendPrivateMessage
)
@log_time
async def on_send_private_message(
    packet: SendPrivateMessage, client_state: ClientState, profile: Profile
) -> None:
    await services.cho.process_message(
        client_state=client_state,
        profile=profile,
        text=packet.text.value,
        recipient=packet.reciever.value,
    )
    return
