import ossapi.enums
from enum import IntEnum


class ScoringType(IntEnum):
    SCOREV1 = 0
    SCOREV2 = 1
    PP = 2

    def to_api_v2(self) -> ossapi.enums.RankingType:
        return {
            ScoringType.SCOREV1: ossapi.enums.RankingType.SCORE,
            ScoringType.SCOREV2: ossapi.enums.RankingType.SCORE,
            ScoringType.PP: ossapi.enums.RankingType.PERFORMANCE,
        }[self]
