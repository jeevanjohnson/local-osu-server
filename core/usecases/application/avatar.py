import core.usecases.domain.profiles as profiles_usecases

def get(user_identifier: int | str) -> str:
    if isinstance(user_identifier, str):
        profile = profiles_usecases.get(user_identifier)

        if profile is None:
            raise ValueError(f"Profile with name '{user_identifier}' does not exist.")

        return profile.avatar_url

    return f"https://a.ppy.sh/{user_identifier}"