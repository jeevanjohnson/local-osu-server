import os
import sys
import asyncio
from typing import Any
from pathlib import Path
from pyimgur import Imgur
from typing import Optional
from objects.mods import Mods
from server import HTTPServer
from typing import TYPE_CHECKING
from aiohttp import ClientSession
from objects.config import Config

if TYPE_CHECKING:
    from objects.player import Player
    from objects.command import Command
    from objects.jsonfile import JsonFile

# config
config = Config()
json_config: 'JsonFile'

# db
pfps: 'JsonFile'
beatmaps: 'JsonFile'
profiles: 'JsonFile'
modified_beatmaps: 'JsonFile'

# paths
modified_txt: Path
osu_exe_path: Optional[Path] = None
songs_folder: Optional[Path] = None
replay_folder: Optional[Path] = None
screenshot_folder: Optional[Path] = None

# session
mode: Optional[Mods] = None
current_profile: dict[str, Any]
player: Optional['Player'] = None
invalid_mods: int = (
    Mods.AUTOPILOT | Mods.RELAX |
    Mods.AUTOPLAY | Mods.CINEMA |
    Mods.TARGET
)

current_cmd: Optional['Command'] = None

# services
http: ClientSession
http_server: HTTPServer
imgur: Optional[Imgur] = None

# constants
default_avatar: bytes
lock = asyncio.Lock()
commands: dict[str, 'Command'] = {}

# checks
using_wsl = (
    sys.platform == 'linux' and
    'microsoft-standard-WSL' in os.uname().release # type: ignore
)