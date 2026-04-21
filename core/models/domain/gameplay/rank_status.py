from enum import IntEnum
import ossapi.enums

from core.osu_protocol.osu.types import osuMapStatus

class RankStatus(IntEnum):
    UNSUBMITTED = 0
    PENDING = 1
    RANKED = 2
    APPROVED = 3
    QUALIFIED = 4
    LOVED = 5

    def ranked(self) -> bool:
        return self in {RankStatus.RANKED, RankStatus.APPROVED}

    def has_leaderboards(self) -> bool:
        return self in {RankStatus.RANKED, RankStatus.APPROVED, RankStatus.QUALIFIED, RankStatus.LOVED}

    @classmethod
    def from_api_v2(cls, ranked_status: ossapi.enums.RankStatus) -> "RankStatus":
        return {
            ossapi.enums.RankStatus.GRAVEYARD: cls.PENDING,
            ossapi.enums.RankStatus.WIP: cls.PENDING,
            ossapi.enums.RankStatus.PENDING: cls.PENDING,
            ossapi.enums.RankStatus.RANKED: cls.RANKED,
            ossapi.enums.RankStatus.APPROVED: cls.APPROVED,
            ossapi.enums.RankStatus.QUALIFIED: cls.QUALIFIED,
            ossapi.enums.RankStatus.LOVED: cls.LOVED,
        }[ranked_status]
    
    @classmethod
    def from_client(cls, ranked_status: osuMapStatus) -> "RankStatus":
        return {
            osuMapStatus.PENDING: cls.PENDING,
            osuMapStatus.RANKED: cls.RANKED,
            osuMapStatus.APPROVED: cls.APPROVED,
            osuMapStatus.QUALIFIED: cls.QUALIFIED,
            osuMapStatus.LOVED: cls.LOVED,
        }[ranked_status]
    
    def to_client(self) -> osuMapStatus:
        return {
            RankStatus.PENDING: osuMapStatus.PENDING,
            RankStatus.RANKED: osuMapStatus.RANKED,
            RankStatus.APPROVED: osuMapStatus.APPROVED,
            RankStatus.QUALIFIED: osuMapStatus.QUALIFIED,
            RankStatus.LOVED: osuMapStatus.LOVED,
        }[self]