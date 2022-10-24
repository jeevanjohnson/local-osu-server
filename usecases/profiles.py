from __future__ import annotations
from typing import Optional
from sqlmodel import Session
import models
from objects.profile import Profile
from sqlmodel import select
import globals


def from_name(profile_name: str) -> Optional[Profile]:
    with Session(globals.database.engine) as database_session:
        statement = select(models.Profile).where(models.Profile.name == profile_name)
        profile = database_session.exec(statement).first()

        if profile is None:
            return None
        else:
            return Profile(
                name=profile.name,
                avatar_url=profile.avatar_url,
            )


def exist(profile_name: str) -> bool:
    """Checks if profile exists in database from name"""
    with Session(globals.database.engine) as database_session:
        statement = select(models.Profile).where(models.Profile.name == profile_name)
        profile = database_session.exec(statement).fetchall()

        if profile:
            return True

    return False


def create(profile_name: str) -> int:
    """Create a new profile"""
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


def all() -> list[Profile]:
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
