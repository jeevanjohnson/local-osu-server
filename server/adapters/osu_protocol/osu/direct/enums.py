from enum import IntEnum, unique


@unique
class ClientRankStatusQuery(IntEnum):
    RANKED = 0
    PENDING = 2
    QUALIFIED = 3
    ALL = 4
    GRAVEYARD = 5
    RANKED_PLAYED = 7
    LOVED = 8
