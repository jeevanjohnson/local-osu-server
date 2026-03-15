"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""
from repositories.sessions import SessionsRepository
from models.database.sessions import Session
from constants import SESSIONS_FILE

def delete_current_session() -> None:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    sessions_repo.delete_current_session()

    return

def create_session(profile_name: str) -> None:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    sessions_repo.create_session({
        "profile_name": profile_name,
        "loaded_beatmap_md5": None,
        "loaded_replay_id": None,
        "current_game_mode": None,
    })
    
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