"""
Purpose/Domain/Concept:
- This file builds the routes related to c*.ppy.sh
"""

from fastapi import APIRouter, Response
from fastapi import Request, Header
from typing import Literal
import usecases.gui
import usecases.bancho
import usecases.sessions
import usecases.profiles
import osuProtocol.server_packets
from osuProtocol.server_packets import osuGameMode, osuCountryCode

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

        login_data = usecases.bancho.parse_login_data(
            await request.body()
        )

        session = usecases.sessions.get_current_session()
        if session is None or session["profile_name"] is None:
            failed_login_response = osuProtocol.server_packets.failed_login_response(
                "No active session found. Please log in through the GUI."
            )

            return Response(
                content=failed_login_response.build(),
                headers={"cho-token": "no-active-session"},
            )

        username = session["profile_name"]

        profile = usecases.profiles.get_profile(username)

        if profile is None:
            failed_login_response = osuProtocol.server_packets.failed_login_response(
                "Profile not found. Please log in through the GUI."
            )

            return Response(
                content=failed_login_response.build(),
                headers={"cho-token": "profile-not-found"},
            )

        friend_ids = profile[username]["friend_ids"]
        country_code = profile[username]["country_code"]
        current_game_mode = session["current_game_mode"]
        if current_game_mode is None:
            current_game_mode = "0"
        else:
            current_game_mode = str(current_game_mode)
        
        rank = profile[username]["performance"][current_game_mode]["rank"]
        ranked_score = profile[username]["performance"][current_game_mode]["ranked_score"]
        accuracy = profile[username]["performance"][current_game_mode]["accuracy"]
        play_count = profile[username]["performance"][current_game_mode]["playcount"]
        total_score = profile[username]["performance"][current_game_mode]["total_score"]
        performance_points = profile[username]["performance"][current_game_mode]["performance_points"]

        successful_login_response = osuProtocol.server_packets.successful_login_response(
            username=username,
            friend_ids=friend_ids,
            utc_offset=login_data["utc_offset"],
            country_code=osuCountryCode(country_code),
            game_mode=osuGameMode(int(current_game_mode)),
            longitude=0.0,
            latitude=0.0,
            rank=rank,
            ranked_score=ranked_score,
            accuracy=accuracy,
            play_count=play_count,
            total_score=total_score,
            performance_points=performance_points,
        )

        return Response(
            content=successful_login_response.build(),
            headers={"cho-token": f"login-successful-for-{username}"},
        )

    # handle other packets that we recieve from the client after login here