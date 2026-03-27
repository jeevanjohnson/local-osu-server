import ossapi.enums
import ossapi.models

from enum import IntEnum, unique


@unique
class osuMapStatus(IntEnum):
    """
    Represents the ranked status of a beatmap.
    """

    NOT_SUBMITTED = -1
    PENDING = 0
    UPDATE_AVAILABLE = 1
    RANKED = 2
    APPROVED = 3
    QUALIFIED = 4
    LOVED = 5

    @property
    def permanent(self) -> bool:
        return self in {
            osuMapStatus.RANKED,
            osuMapStatus.APPROVED,
            osuMapStatus.LOVED,
        }

    def ranked(self) -> bool:
        return self in {
            osuMapStatus.RANKED,
            osuMapStatus.APPROVED,
        }

    def has_leaderboard(self) -> bool:
        return self in {
            osuMapStatus.RANKED,
            osuMapStatus.APPROVED,
            osuMapStatus.QUALIFIED,
            osuMapStatus.LOVED,
        }

    @classmethod
    def from_api_v2(cls, ranked_status: ossapi.enums.RankStatus) -> "osuMapStatus":
        return {
            ossapi.enums.RankStatus.GRAVEYARD: cls.PENDING,
            ossapi.enums.RankStatus.WIP: cls.PENDING,
            ossapi.enums.RankStatus.PENDING: cls.PENDING,
            ossapi.enums.RankStatus.RANKED: cls.RANKED,
            ossapi.enums.RankStatus.APPROVED: cls.APPROVED,
            ossapi.enums.RankStatus.QUALIFIED: cls.QUALIFIED,
            ossapi.enums.RankStatus.LOVED: cls.LOVED,
        }[ranked_status]

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


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