import re
import asyncio
from typing import Any
from pathlib import Path
from typing import Union
from pyimgur import Imgur
from typing import Callable
from typing import Optional
from typing import TYPE_CHECKING
from aiohttp import ClientSession

if TYPE_CHECKING:
    from objects.file import File
    from objects.player import Player
    from objects.jsonfile import JsonFile

pfps: 'JsonFile'
modified_txt: Path
http: ClientSession
beatmaps: 'JsonFile'
profiles: 'JsonFile'
default_avatar: bytes
lock = asyncio.Lock()
modified_beatmaps: 'JsonFile'
imgur: Optional[Imgur] = None
player: Optional['Player'] = None
osu_exe_path: Optional[Path] = None
songs_folder: Optional[Path] = None
replay_folder: Optional['File'] = None
screenshot_folder: Optional[Path] = None
current_profile: Optional[dict[str, Any]] = None
handlers: dict[Union[str, re.Pattern], Callable] = {}