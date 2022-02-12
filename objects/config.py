import orjson
from pathlib import Path
from typing import Optional
from typing import Iterable
from typing import TypedDict

class MenuIcon(TypedDict):
    image_link: Optional[str]
    click_link: Optional[str]

class Paths(TypedDict):
    osu_path: Optional[str]
    songs: Optional[str]
    replay: Optional[str]
    screenshots: Optional[str]

class Config:
    def __init__(self, **kwargs) -> None:
        self.paths = Paths(
            osu_path = None,
            songs = None,
            replay = None,
            screenshots = None
        )

        self.pp_leaderboard: bool = True
        self.ping_user_when_recent_score: bool = False

        self.menu_icon = MenuIcon(
            image_link = None,
            click_link = None
        )

        self.command_prefix: str = '!'
        self.show_pp_for_personal_best: bool = True
        self.amount_of_scores_on_lb: int = 100

        self.auto_update: bool = True
        self.disable_funorange_maps: bool = False
        self.osu_api_key: Optional[str] = None
        self.imgur_client_id: Optional[str] = None
        self.osu_daily_api_key: Optional[str] = None
        self.seasonal_bgs: Optional[Iterable[str]] = []
        self.osu_username: Optional[str] = None
        self.osu_password: Optional[str] = None

        self.__dict__.update(kwargs)
    
    @classmethod
    def from_path(cls, path: Path) -> 'Config':
        return cls(
            **(orjson.loads(path.read_bytes()) or {})
        )