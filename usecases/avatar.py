"""
Purpose/Domain/Concept:
- This file contains the logic related to handling requests regarding avatars (a.ppy.sh).
"""

from pathlib import Path

from repositories.profiles import (
    ProfilesRepository,
)


async def profile(name: str) -> str | Path | None:
    profile_repo = ProfilesRepository()

    profile = await profile_repo.get(name)

    if profile is None:
        return None

    if profile.profile_picture is None:
        return "https://a.ppy.sh/"

    return profile.profile_picture
