from enum import IntEnum, unique


@unique
class LeaderboardType(IntEnum):
    """
    Types of leaderboards that can be requested.
    """

    LOCAL = 0
    TOP = 1
    MODS = 2
    FRIENDS = 3
    COUNTRY = 4
