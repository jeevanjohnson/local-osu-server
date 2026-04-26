
from enum import IntEnum
import rosu_pp_py as rosu
import ossapi.enums
from core.osu_protocol.domain.enums import osuGameMode
from jays_tools.architecture import DomainModel


class GameMode(DomainModel, IntEnum):
    STANDARD = 0
    TAIKO = 1
    CATCH = 2
    MANIA = 3

    def __str__(self) -> str:
        return self.to_osu_website()

    def to_osu_website(self) -> str:
        return {
            self.STANDARD: "osu",
            self.TAIKO: "taiko",
            self.CATCH: "fruits",
            self.MANIA: "mania",
        }[self]

    def to_rosu(self) -> rosu.GameMode:
        return {
            self.STANDARD: rosu.GameMode.Osu,
            self.TAIKO: rosu.GameMode.Taiko,
            self.CATCH: rosu.GameMode.Catch,
            self.MANIA: rosu.GameMode.Mania,
        }[self]

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

    @classmethod
    def from_client(cls, client_value: osuGameMode) -> "GameMode":
        return {
            osuGameMode.STANDARD: cls.STANDARD,
            osuGameMode.TAIKO: cls.TAIKO,
            osuGameMode.CATCH_THE_BEAT: cls.CATCH,
            osuGameMode.MANIA: cls.MANIA,
        }[client_value]
