import core.usecases.application.authentication as auth_usecases
from fastapi import Depends, Header, Request
import core.osu_protocol.cho.server as cho_server
import core.osu_protocol.cho.client as cho_client
from core.osu_protocol.cho.client import parse_login_data
import core.services.cho as cho_services
from typing import Literal
from server.usecases.domain.player import Player

async def player() -> Player | None:
    result = auth_usecases.current_logged_in_profile()

    if result is None:
        return None

    profile_name, profile = result

    return Player(profile_name)

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