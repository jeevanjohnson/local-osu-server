import core.usecases.application.authentication as auth_usecases

def user_identifier(user_id: int) -> int | str:
    if user_id == 2:
        result = auth_usecases.current_logged_in_profile()
        
        if result is None:
            raise Exception("No profile is currently logged in.")
        
        profile_name, profile = result

        return profile_name

    return user_id