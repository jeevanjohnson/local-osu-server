from jays_tools.sql_database import MigratableSQLModel
from pydantic import Field

from core.adapters.osu_protocol.cho.server import osuCountryCode
import random


def seasonal_backgrounds_factory() -> list[str]:
    return [
        "https://raw.githubusercontent.com/jeevanjohnson/local-osu-server/refs/heads/2026/resources/seasonal_bg.png"
    ]


def random_country_code_factory() -> osuCountryCode:
    return random.choice(
        list(osuCountryCode)
    )


class ProfileV1(MigratableSQLModel, table=True):
    name: str = Field(default="")
    avatar_url: str = Field(default="https://a.ppy.sh/")
    friend_ids: list[int] = Field(default=[])
    country_code: osuCountryCode = Field(
        default_factory=random_country_code_factory
    )
    notes: str = Field(default="")
    bbc_code_bio: str = Field(default="")
    seasonal_backgrounds: list[str] = Field(
        default_factory=seasonal_backgrounds_factory
    )


Profile = ProfileV1
