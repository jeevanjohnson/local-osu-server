"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""
from repositories.sessions import SessionRepository
from models.database.sessions import CurrentSession as Session
from constants import SESSIONS_FILE
from osuProtocol.server_packets import Notification, Packets, Packet, bytes_to_string, osuAction, osuGameMode, osuGameMode, osuMods, string_to_bytes, PlayerStats
import usecases.profiles

def delete_current_session() -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    sessions_repo.delete_current_session()

    return

def create_session(profile_name: str) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    sessions_repo.create_session(profile_name)

    return 

def session_exists() -> bool:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    session = sessions_repo.get_current_session()

    if session is None:
        return False
    
    return True

def get_current_session() -> Session | None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    session = sessions_repo.get_current_session()

    if session is None:
        print("Attempted to retrieve current session but no active session was found.")
        return None

    return session

def update_current_session(session: Session) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    # Catch error when no session exists
    sessions_repo.update_current_session(session)

    return

# TODO: Log decorator that catches and logs errors and neatly formats them with json so when dev ask
# for logs its easily readable and replicatable.
# TODO: log parameter being "handled_errors" that is a list of error types that are expected and handled so they dont get logged as errors 
#             but rather warnings or info depending on the severity of the error. 
# (for example, if a session is not found when trying to update it, that is an expected error that can happen when the server receives a request from the client before the user has logged in through the GUI, so it should be handled and logged as a warning rather than an error.)
# TODO: idk if i need this anymore
def enqueue_packets_to_current_session(packets: Packets | Packet) -> Session | None:
    session = get_current_session()
    
    if session is None:
        print("Attempted to enqueue packets but no active session was found.")
        return
    
    session.packet_queue += packets.build()

    update_current_session(session)

    return session

def clear_packet_queue() -> Session | None:
    session = get_current_session()
    if session is None:
        print("Attempted to clear packet queue but no active session was found.")
        return

    session.packet_queue = b""
    update_current_session(session)

    return session

def update_in_game_stats() -> None:
    session = get_current_session()
    if session is None:
        print("Attempted to update stats but no active session was found.")
        return # TODO: Raise Error
    
    profile = usecases.profiles.get_profile(session.profile_name)
    if profile is None:
        print("Attempted to update stats but the associated profile was not found.")
        return

    ranked_score = profile.performance[session.current_game_mode].ranked_score
    accuracy = profile.performance[session.current_game_mode].accuracy
    play_count = profile.performance[session.current_game_mode].playcount
    total_score = profile.performance[session.current_game_mode].total_score
    rank = profile.performance[session.current_game_mode].rank
    performance_points = profile.performance[session.current_game_mode].performance_points

    enqueue_packets_to_current_session(
        PlayerStats(
            user_id=2,
            action=session.osu_client.status,
            info_text=session.osu_client.status_message,
            beatmap_md5=session.latest_beatmap.md5,
            mods=session.latest_enabled_mods,
            game_mode=session.current_game_mode,
            beatmap_id=session.latest_beatmap.id,
            ranked_score=ranked_score,
            accuracy=accuracy,
            play_count=play_count,
            total_score=total_score,
            rank=rank,
            performance_points=performance_points
        )
    )

    return