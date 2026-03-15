"""
Purpose/Domain/Concept:
- This file contains the logic related to handling requests regarding avatars (a.ppy.sh).
"""
import os
from pathlib import Path

from repositories.sessions import SessionsRepository
from repositories.profiles import ProfilesRepository
from constants import SESSIONS_FILE, PROFILES_FILE

def get_session_avatar() -> str | Path | None:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    session = sessions_repo.get_current_session()
    if session is None or session["profile_name"] is None:
        return None

    profile_name = session["profile_name"]
    profile = profiles_repo.get_profile(profile_name)
    if profile is None:
        return None

    if profile[profile_name]["profile_picture"] is None:
        return "https://a.ppy.sh/"

    profile_picture = profile[profile_name]["profile_picture"]
    if profile_picture is None:
        return "https://a.ppy.sh/"

    if os.path.exists(profile_picture):
        return profile_picture

    return profile_picture