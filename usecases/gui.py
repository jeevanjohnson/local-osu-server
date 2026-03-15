
"""
Purpose/Domain/Concept:
- This file contains the logic for handling/checking GUI-related operations.
"""

from repositories.profiles import ProfilesRepository
from repositories.sessions import SessionsRepository
from constants import PROFILES_FILE, SESSIONS_FILE

def logged_in() -> bool:
    sessions_repo = SessionsRepository(SESSIONS_FILE)
    session = sessions_repo.get_current_session()
    if session is None or session["profile_name"] is None:
        return False

    profile_name = session["profile_name"]

    profile_repo = ProfilesRepository(PROFILES_FILE)
    profile = profile_repo.get_profile(profile_name)
    
    if profile is None:
       return False
    
    return True