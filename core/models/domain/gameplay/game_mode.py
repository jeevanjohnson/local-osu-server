from enum import IntEnum
import ossapi.enums

class GameMode(IntEnum):
    STANDARD = 0
    TAIKO = 1
    CATCH = 2
    MANIA = 3

    @classmethod
    def from_api_v2(cls, api_value: ossapi.enums.GameMode) -> "GameMode":
        return {
            ossapi.enums.GameMode.OSU: cls.STANDARD,
            ossapi.enums.GameMode.TAIKO: cls.TAIKO,
            ossapi.enums.GameMode.CATCH: cls.CATCH,
            ossapi.enums.GameMode.MANIA: cls.MANIA,
        }[api_value]
    
    def to_api_v2(self) -> ossapi.enums.GameMode:
        return {
            self.STANDARD: ossapi.enums.GameMode.OSU,
            self.TAIKO: ossapi.enums.GameMode.TAIKO,
            self.CATCH: ossapi.enums.GameMode.CATCH,
            self.MANIA: ossapi.enums.GameMode.MANIA,
        }[self]