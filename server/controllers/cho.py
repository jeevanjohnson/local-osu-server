from typing import get_type_hints
from typing import Callable, Coroutine, Any
from typing import Any, Callable, Coroutine, Literal

from fastapi import APIRouter, Header, Request, Response

from server.adapters.osu_protocol.cho.packets.packets import (
    ClientPacketStream,
    ClientPacketBase,
    LogOut,
    UserStatsRequest,
    FriendRemove,
    FriendAdd,
    SendMessage,
    StatusChanged
)
from server.usecases.domain.player import PlayerDomainUseCase


bancho = APIRouter()

PLAYER_DOMAIN_USECASE = PlayerDomainUseCase()


@bancho.post("/")
async def client_request_handler(
    request: Request,
    osu_token: str | None = Header(None),
    user_agent: Literal["osu!"] = Header(...),
):
    if osu_token is None:
        # TODO: login response
        return

    packet_stream = ClientPacketStream.from_osu_client(
        await request.body()
    )

    for packet in packet_stream:
        packet_type = type(packet)

        if packet_type not in PACKET_HANDLERS:
            continue

        await PACKET_HANDLERS[packet_type](packet)

    outgoing_packets = await PLAYER_DOMAIN_USECASE.clear_outgoing_packets()
    return Response(outgoing_packets)


type PACKET_HANDLER = Callable[..., Coroutine[Any, Any, None]]

PACKET_HANDLERS: dict[
    type[ClientPacketBase], PACKET_HANDLER
] = {}


def register_packet_handler(func: PACKET_HANDLER) -> PACKET_HANDLER:
    packet_type = get_type_hints(func)["packet"]
    PACKET_HANDLERS[packet_type] = func
    return func


@register_packet_handler
async def on_status_changed(
    packet: StatusChanged
) -> None:
    await PLAYER_DOMAIN_USECASE.update_status(
        packet.status,
        packet.status_message
    )


@register_packet_handler
async def on_logout(
    packet: LogOut
) -> None:
    if not await PLAYER_DOMAIN_USECASE.valid_logout():
        return

    await PLAYER_DOMAIN_USECASE.logout()


@register_packet_handler
async def user_stats_request(
    packet: UserStatsRequest
) -> None:

    user_ids = packet.user_ids

    if 3 in user_ids:
        user_ids.remove(3)

    if 2 not in user_ids:
        user_ids.append(2)

    # TODO: implement stats for other users (friends)


@register_packet_handler
async def friend_remove(
    packet: FriendRemove
) -> None:
    await PLAYER_DOMAIN_USECASE.remove_friend(packet.id)


@register_packet_handler
async def on_friend_add(
    packet: FriendAdd
) -> None:
    await PLAYER_DOMAIN_USECASE.notify(
        "Adding friends this way is not supported in LOS! ʕ•̫͡•ʔ\n"
        "Please refer to the interface for adding friends."
    )


@register_packet_handler
async def on_message(
    packet: SendMessage
) -> None:
    # TODO: messages
    return
