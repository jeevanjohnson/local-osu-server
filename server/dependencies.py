import core.usecases.domain.authentication as auth_usecases
from fastapi import Depends, Header, Request
import server.adapters.osu_protocol.cho.server as cho_server
import server.adapters.osu_protocol.cho.client as cho_client
from server.adapters.osu_protocol.cho.client import parse_login_data
import core.services.cho as cho_services
from typing import Literal
from core.usecases.domain.player import Player
import core.usecases.domain.osu_api as osu_api_usecases


async def login_response(
    request: Request,
    osu_token: str | None = Header(None),
    user_agent: Literal["osu!"] = Header(...),
    player: Player | None = Depends(player)
) -> cho_server.Packets | None:
    if osu_token:
        return None

    if player is None:
        return cho_server.login_failed("You must be logged in through the GUI to use the osu! client.")

    try:
        osu_api_usecases.get_api_client()
    except osu_api_usecases.InvalidOsuApiCredentialsError:
        return cho_server.login_failed("Invalid osu! API credentials. Please set them up in the GUI to use the osu! client.")

    return await cho_services.login(
        player=player,
        login_data=parse_login_data(await request.body())
    )


async def incoming_packets(
    request: Request,
    osu_token: str | None = Header(None),
    user_agent: Literal["osu!"] = Header(...),
) -> cho_client.Packets:
    if osu_token is None:
        return cho_client.Packets(b"")

    packets = cho_client.Packets(await request.body())
    packets.read()

    return packets
