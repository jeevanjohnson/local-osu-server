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
http: ClientSession
beatmaps: 'JsonFile'
profiles: 'JsonFile'
replay_folder: 'File'
default_avatar: bytes
lock = asyncio.Lock()
imgur: Optional[Imgur]
songs_folder: Optional[Path]
screenshot_folder: Optional[Path]
player: Optional['Player'] = None
current_profile: Optional[dict[str, Any]] = None
handlers: dict[Union[str, re.Pattern], Callable] = {}