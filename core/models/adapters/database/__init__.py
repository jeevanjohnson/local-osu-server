from jays_tools.sql_database import MigratableSQLModel
from typing import Type
from .snapshots import SnapShot
from .osu_file_locations import OsuFileLocations
from .interface import InterfaceState
from .profile import Profile
from .client_state import ClientState
from .settings import ProfileSettings
from .performance import Performance
from .server_settings import ServerSettings

ALL_TABLES: list[Type[MigratableSQLModel]] = [
    SnapShot,
    OsuFileLocations,
    InterfaceState,
    Profile,
    ClientState,
    ProfileSettings,
    Performance,
    ServerSettings
]

__all__ = ["ALL_TABLES"]
