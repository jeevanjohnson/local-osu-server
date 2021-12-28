import os
import re
import sys
import asyncio
from typing import Any
from pathlib import Path
from typing import Union
from pyimgur import Imgur
from typing import Callable
from typing import Optional
from objects.mods import Mods
from typing import TYPE_CHECKING
from aiohttp import ClientSession

if TYPE_CHECKING:
    from objects.file import File
    from objects.player import Player
    from objects.command import Command
    from objects.jsonfile import JsonFile

# db
pfps: 'JsonFile'
beatmaps: 'JsonFile'
profiles: 'JsonFile'
modified_beatmaps: 'JsonFile'

# paths
modified_txt: Path
osu_exe_path: Optional[Path] = None
songs_folder: Optional[Path] = None
replay_folder: Optional['File'] = None
screenshot_folder: Optional[Path] = None

# session
mode: Optional[Mods] = None
player: Optional['Player'] = None
current_profile: Optional[dict[str, Any]] = None
invalid_mods: int = (
    Mods.AUTOPILOT | Mods.RELAX |
    Mods.AUTOPLAY | Mods.CINEMA |
    Mods.TARGET
)._value_

current_cmd: Optional['Command'] = None

# services
http: ClientSession
imgur: Optional[Imgur] = None

# constants
default_avatar: bytes
lock = asyncio.Lock()
commands: dict[str, 'Command'] = {}
handlers: dict[Union[str, re.Pattern], Callable] = {}

# checks
using_wsl = (
    sys.platform == 'linux' and
    'microsoft-standard-WSL' in os.uname().release # type: ignore
)