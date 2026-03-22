"""
Purpose/Domain/Concept:
- This file contains the logic related to handling requests regarding avatars (a.ppy.sh).
"""

from pathlib import Path

import usecases.profiles
import usecases.sessions
from adapters.app_logger import app_logger
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError


@app_logger.log(msg="usecase get session avatar")
async def get_session_avatar() -> str | Path | None:
    try:
        session = await usecases.sessions.require_current_session()
    except SessionNotFoundError:
        return None

    profile_name = session.profile_name

    try:
        profile = await usecases.profiles.require_profile(profile_name)
    except ProfileNotFoundError:
        return None

    if profile.profile_picture is None:
        return "https://a.ppy.sh/"

    return profile.profile_picture
