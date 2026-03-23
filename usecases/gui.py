"""
Purpose/Domain/Concept:
- This file contains the logic for handling/checking GUI-related operations.
"""

from adapters import log, log_time
from constants import PROFILES_FILE, SESSIONS_FILE
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from repositories.profiles import ProfilesRepository
from repositories.sessions import SessionRepository


@log_time
async def logged_in() -> bool:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    profile_repo = ProfilesRepository(PROFILES_FILE)

    try:
        session = await sessions_repo.require_current_session()
    except SessionNotFoundError:
        log.warning(
            "Attempted to check if user is logged in but no active session was found."
        )
        return False

    try:
        await profile_repo.require_profile(session.profile_name)
    except ProfileNotFoundError:
        return False

    return True
