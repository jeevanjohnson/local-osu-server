from enum import unique
from enum import IntEnum

@unique
class LeaderboardTypes(IntEnum):
    LOCAL   = 0
    TOP     = 1
    MODS    = 2
    FRIENDS = 3
    COUNTRY = 4