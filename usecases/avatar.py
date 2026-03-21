"""
Purpose/Domain/Concept:
- This file contains the logic related to handling requests regarding avatars (a.ppy.sh).
"""

from pathlib import Path

from constants import PROFILES_FILE, SESSIONS_FILE
from repositories.profiles import ProfilesRepository
from repositories.sessions import SessionRepository


def get_session_avatar() -> str | Path | None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    session = sessions_repo.get_current_session()
    if session is None:
        return None

    profile_name = session.profile_name

    profile = profiles_repo.get_profile(profile_name)
    if profile is None:
        return None

    if profile.profile_picture is None:
        return "https://a.ppy.sh/"

    return profile.profile_picture
