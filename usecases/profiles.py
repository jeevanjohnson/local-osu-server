from __future__ import annotations
from sqlmodel import Session
import models
from objects.profile import Profile
from sqlmodel import select
import globals


def profile_exist(profile_name: str) -> bool:
    with Session(globals.database.engine) as database_session:
        statement = select(models.Profile).where(models.Profile.name == profile_name)
        profile = database_session.exec(statement).fetchall()

        if profile:
            return True

    return False


def create_profile(profile_name: str) -> int:
    profile_id = 0

    with Session(globals.database.engine) as database_session:
        profiles: list[models.Profile] = database_session.query(models.Profile).all()

        new_profile = models.Profile(
            name=profile_name,
            avatar_url=None,
            id=len(profiles) + 1,
        )
        database_session.add(new_profile)

        database_session.commit()

        profile_id = new_profile.id

    return profile_id


def get_all() -> list[Profile]:
    """Returns a list of all profiles in the database."""
    with Session(globals.database.engine) as database_session:
        profiles: list[models.Profile] = database_session.query(models.Profile).all()

    if profiles:
        return [
            Profile(
                name=profile.name,
                avatar_url=profile.avatar_url,
            )
            for profile in profiles
        ]
    else:
        return []
