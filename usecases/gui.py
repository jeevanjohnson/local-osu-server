
"""
Purpose/Domain/Concept:
- This file contains the logic for handling/checking GUI-related operations.
"""

from repositories.profiles import ProfilesRepository
from repositories.sessions import SessionRepository
from constants import PROFILES_FILE, SESSIONS_FILE

def logged_in() -> bool:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    profile_repo = ProfilesRepository(PROFILES_FILE)
    
    session = sessions_repo.get_current_session()
    if session is None:
        print("Attempted to check if user is logged in but no active session was found.")
        return False
    
    profile = profile_repo.get_profile(session.profile_name)
    
    if profile is None:
       return False
    
    return True