"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""
from repositories.sessions import SessionsRepository
from models.database.sessions import Session
from constants import SESSIONS_FILE
from osuProtocol.server_packets import Packets, bytes_to_string, string_to_bytes
import base64

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

def enqueue_packets_to_current_session(packets: Packets) -> Session | None:
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