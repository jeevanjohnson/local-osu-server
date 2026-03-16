"""
Purpose/Domain/Concept:
- This file builds the routes related to c*.ppy.sh
"""

from fastapi import APIRouter, Response
from fastapi import Request, Header
from typing import Literal, TypeVar
import usecases.gui
import usecases.bancho
import usecases.sessions
import usecases.profiles
import usecases.beatmaps
import osuProtocol.server_packets
from osuProtocol.server_packets import bytes_to_string, osuGameMode, osuCountryCode, string_to_bytes, ClientRelog
from osuProtocol.server_packets import PlayerStats, Packets as ServerPackets, osuAction, osuMods, osuGameMode
from osuProtocol.client_packets import Packets, ClientPackets, ChangeAction, Packet, Ping, LogOut
from typing import Callable

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

        session["client_opened"] = True
        usecases.sessions.update_current_session(session)

        return Response(
            content=successful_login_response.build(),
            headers={"cho-token": f"login-successful-for-{username}"},
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
            print(f"Received packet with ID {ClientPackets(packet._id).name} but no handler is registered for this packet type.")
            continue

        emergency_response = PACKET_HANDLERS[ClientPackets(packet._id)](packet)

        if emergency_response is not None:
            print((
                f"Emergency response triggered for packet ID {ClientPackets(packet._id).name}. "
                "Sending response to client and skipping remaining packets in the queue."
            ))
            return Response(
                content=emergency_response,
            )

    packet_queue = session["packet_queue"]
    if packet_queue is None:
        return Response(content=b"")

    response_packets = string_to_bytes(packet_queue)

    session["packet_queue"] = None
    usecases.sessions.update_current_session(session)

    return Response(content=response_packets)

PACKET_HANDLERS: dict[ClientPackets, Callable[[Packet], bytes | None]] = {}
PacketType = TypeVar("PacketType", bound=Packet)

def register_packet_handler(packet_id: ClientPackets, packet_type: type[PacketType]):
    def inner(func: Callable[[PacketType], bytes | None]):
        def wrapper(packet: Packet) -> bytes | None:
            if not isinstance(packet, packet_type):
                return None

            return func(packet)

        PACKET_HANDLERS[packet_id] = wrapper
        return func
    return inner

@register_packet_handler(
    ClientPackets.PING,
    packet_type=Ping
)
def handle_ping(packet: Ping):
    return

@register_packet_handler(
    ClientPackets.CHANGE_ACTION, 
    packet_type=ChangeAction
)
def on_action_change(packet: ChangeAction):
    session = usecases.sessions.get_current_session()
    if session is None or session["profile_name"] is None:
        return osuProtocol.server_packets.client_relog_response().build()
    
    profile_name = session["profile_name"]

    profile = usecases.profiles.get_profile(profile_name)
    if profile is None:
        return osuProtocol.server_packets.client_relog_response().build()

    session["current_game_mode"] = packet.current_game_mode.value

    # this sections should probably not exists cause of osu-web
    beatmap_md5 = packet.beatmap_md5.value
    if beatmap_md5 == "":
        beatmap_md5 = None

    beatmap_id = packet.beatmap_id.value
    if beatmap_id == 0:
        beatmap_id = None

    beatmap = usecases.beatmaps.get_beatmap(
        beatmap_md5 = beatmap_md5,
        beatmap_id = beatmap_id
    )

    if beatmap is not None:
        session["loaded_beatmap_set_id"] = beatmap.beatmapset_id
    else:
        session["loaded_beatmap_set_id"] = None
    # this sections should probably not exists cause of osu-web ^

    # will have to update readme cause of api key grabbing
    # also import score button would be epic

    # Persist gameplay/session state first so enqueue reads the latest session snapshot.
    usecases.sessions.update_current_session(session)

    ranked_score = profile[profile_name]["performance"][str(packet.current_game_mode.value)]["ranked_score"]
    accuracy = profile[profile_name]["performance"][str(packet.current_game_mode.value)]["accuracy"]
    play_count = profile[profile_name]["performance"][str(packet.current_game_mode.value)]["playcount"]
    total_score = profile[profile_name]["performance"][str(packet.current_game_mode.value)]["total_score"]
    rank = profile[profile_name]["performance"][str(packet.current_game_mode.value)]["rank"]
    performance_points = profile[profile_name]["performance"][str(packet.current_game_mode.value)]["performance_points"]

    packet_enqueue = ServerPackets()
    packet_enqueue += PlayerStats(
        user_id=2,
        action= osuAction(packet.action.value),
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
        performance_points=performance_points
    )

    updated_session = usecases.sessions.enqueue_packets_to_current_session(packet_enqueue)

    if updated_session is None:
        return osuProtocol.server_packets.client_relog_response().build()
    
@register_packet_handler(
    ClientPackets.LOGOUT,
    packet_type=LogOut
)
def on_logout(packet: LogOut):
    session = usecases.sessions.get_current_session()
    if session is None or session["profile_name"] is None:
        return

    session["current_game_mode"] = None
    session["loaded_beatmap_id"] = None
    session["loaded_beatmap_md5"] = None
    session["loaded_beatmap_set_id"] = None
    session["loaded_replay_id"] = None
    session["packet_queue"] = None
    session["client_opened"] = False

    usecases.sessions.update_current_session(session)