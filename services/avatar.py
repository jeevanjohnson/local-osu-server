from pathlib import Path

import usecases.application.client.state
import usecases.avatar


async def get(user_id: int) -> str | Path:
    if user_id != 2:
        return f"https://a.ppy.sh/{user_id}"

    profile_name = await usecases.application.client.state.profile_name()

    avatar = await usecases.avatar.profile(profile_name)

    if avatar is None:
        return "https://a.ppy.sh/2"

    return avatar
