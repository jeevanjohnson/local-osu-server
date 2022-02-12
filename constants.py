import re
from objects import Mods
from typing import Optional
from typing import TypedDict
class InvalidMods:
    Standard = (
        Mods.AUTOPILOT | Mods.RELAX |
        Mods.AUTOPLAY | Mods.CINEMA |
        Mods.TARGET
    )

    AutoPilot = (
        Mods.RELAX | Mods.AUTOPLAY |
        Mods.CINEMA | Mods.TARGET
    )

    Relax = (
        Mods.AUTOPILOT | Mods.AUTOPLAY |
        Mods.CINEMA | Mods.TARGET
    )

class ParsedParams(TypedDict):
    filename: str
    mods: int
    mode: int
    rank_type: int
    set_id: int
    md5: str
    name_data: Optional[re.Match]

CHO_TOKEN = str
BODY = bytearray

CHANNEL = tuple[str, str]
CHANNELS: list[CHANNEL] = [
    # name, desc
    ('#osu', 'x'),
    ('#recent', 'shows recently submitted scores!'),
    ('#tops', 'shows top plays, as well as updates them!')
]