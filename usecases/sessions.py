"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""
from repositories.sessions import SessionsRepository
from models.database.sessions import Session
from constants import SESSIONS_FILE
from osuProtocol.server_packets import Notification, Packets, Packet, bytes_to_string, osuAction, osuGameMode, osuGameMode, osuMods, string_to_bytes, PlayerStats
import usecases.profiles

def delete_current_session() -> None:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    sessions_repo.delete_current_session()

    return

def create_session(profile_name: str) -> None:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    sessions_repo.create_session(
        Session(
            profile_name=profile_name,
            loaded_beatmap_md5=None,
            loaded_replay_id=None,
            current_game_mode=None,
            packet_queue=None,
            loaded_beatmap_id=None,
            loaded_beatmap_set_id=None,
            client_opened=False,
            status=None,
            status_message=None,
            loaded_mods=None
        )
    )

    return 

def session_exists() -> bool:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    session = sessions_repo.get_current_session()

    if session is None:
        return False

    if session["profile_name"] is None:
        return False

    return True

def get_current_session() -> Session | None:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    session = sessions_repo.get_current_session()

    if session is None:
        return None

    return session

def update_current_session(session: Session) -> None:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    sessions_repo.update_current_session(session)

    return

def enqueue_packets_to_current_session(packets: Packets | Packet) -> Session | None:
    session = get_current_session()
    if session is None:
        print("Attempted to enqueue packets but no active session was found.")
        return
    
    if session["profile_name"] is None:
        print("Attempted to enqueue packets but the active session has no profile name.")
        return

    if session["packet_queue"] is None:
        session["packet_queue"] = packets.build_str()
    else:
        existing_packets = string_to_bytes(session["packet_queue"])
        queued_packets = existing_packets + packets.build()
        session["packet_queue"] = bytes_to_string(queued_packets)

    update_current_session(session)

    return session

def clear_packet_queue() -> Session | None:
    session = get_current_session()
    if session is None:
        print("Attempted to clear packet queue but no active session was found.")
        return
    
    if session["profile_name"] is None:
        print("Attempted to clear packet queue but the active session has no profile name.")
        return

    session["packet_queue"] = None
    update_current_session(session)

    return session

def update_in_game_stats() -> None:
    session = get_current_session()
    if session is None:
        print("Attempted to update stats but no active session was found.")
        return
    
    if session["profile_name"] is None:
        print("Attempted to update stats but the active session has no profile name.")
        return
    
    profile = usecases.profiles.get_profile(session["profile_name"])
    if profile is None:
        print("Attempted to update stats but the associated profile was not found.")
        return
    
    profile_name = session["profile_name"]
    
    beatmap_md5 = session["loaded_beatmap_md5"]
    if beatmap_md5 is None:
        beatmap_md5 = ""
    
    action = session["status"]
    if action is None:
        action = osuAction.Idle
    else:
        action = osuAction(action)

    info_text = session["status_message"]
    if info_text is None:
        info_text = ""

    mods = session["loaded_mods"]
    if mods is None:
        mods = osuMods.NOMOD
    else:
        mods = osuMods(mods)

    game_mode = session["current_game_mode"]
    if game_mode is None:
        game_mode = "0"
    else:
        game_mode = str(game_mode)
    
    beatmap_id = session["loaded_beatmap_id"]
    if beatmap_id is None:
        beatmap_id = 0

    ranked_score = profile[profile_name]["performance"][game_mode]["ranked_score"]
    accuracy = profile[profile_name]["performance"][game_mode]["accuracy"]
    play_count = profile[profile_name]["performance"][game_mode]["playcount"]
    total_score = profile[profile_name]["performance"][game_mode]["total_score"]
    rank = profile[profile_name]["performance"][game_mode]["rank"]
    performance_points = profile[profile_name]["performance"][game_mode]["performance_points"]

    game_mode = osuGameMode(int(game_mode))

    enqueue_packets_to_current_session(
        PlayerStats(
            user_id=2,
            action=action,
            info_text=info_text,
            beatmap_md5=beatmap_md5,
            mods=mods,
            game_mode=game_mode,
            beatmap_id=beatmap_id,
            ranked_score=ranked_score,
            accuracy=accuracy,
            play_count=play_count,
            total_score=total_score,
            rank=rank,
            performance_points=performance_points
        )
    )

    return