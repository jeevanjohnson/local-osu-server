import re
import base64
import asyncio
import packets
import colorama
import pyttanko as oppai
from typing import Union
from pathlib import Path
from colorama import Fore
from typing import Literal
from typing import Optional
from typing import Callable
from constants import BUTTON
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects import Score
    from objects import Beatmap
    from objects import BanchoScore
    from objects import ModifiedBeatmap

try:
    from ext import glob
except ImportError:
    pass

colorama.init(autoreset=True)

Color = Fore

PP = float
ACCURACY = float
SCORE = Union['Score', 'BanchoScore']
def calculator(
    score: SCORE, bmap: Union['Beatmap', 'ModifiedBeatmap', oppai.beatmap],
    stars: Optional[oppai.diff_calc] = None
) -> tuple[PP, ACCURACY]:
    """PP calculator (easy to work with and change whenever needed)"""
    if not isinstance(bmap, oppai.beatmap):
        file = bmap.map_file
    else:
        file = bmap
    
    if 'BanchoScore' not in str(type(score)): # avoids merge conflicts
        if not stars:
            stars = oppai.diff_calc().calc(file, score.mods) # type: ignore
        
        pp, *_, acc_percent = oppai.ppv2(
            aim_stars = stars.aim, 
            speed_stars = stars.speed, 
            bmap = file, 
            mods = score.mods, # type: ignore
            n300 = score.n300, # type: ignore
            n100 = score.n100, # type: ignore
            n50 = score.n50, # type: ignore
            nmiss = score.nmiss, # type: ignore
            combo = score.max_combo # type: ignore
        )
    else:
        mods = int(score.enabled_mods) # type: ignore
        if not stars:
            stars = oppai.diff_calc().calc(file, mods)
        
        pp, *_, acc_percent = oppai.ppv2(
            aim_stars = stars.aim, 
            speed_stars = stars.speed, 
            bmap = file, 
            mods = mods,
            n300 = int(score.count300), # type: ignore
            n100 = int(score.count100), # type: ignore
            n50 = int(score.count50), # type: ignore
            nmiss = int(score.countmiss), # type: ignore
            combo = int(score.maxcombo) # type: ignore
        )

        score.pp = pp

    return (pp, acc_percent)

# TODO: rethink of this
# starting to see flaws
iterators = (list, tuple)
PATH = Union[
    str, re.Pattern, 
    list[Union[str, re.Pattern]], 
    tuple[Union[str, re.Pattern]]
]
def handler(target: PATH) -> Callable:
    def inner(func: Callable) -> Callable:
        if isinstance(target, iterators):
            for i in target:
                glob.handlers[i] = func
        else:
            glob.handlers[target] = func
        return func
    return inner

def is_path(p: str) -> Union[Path, Literal[False]]:
    path = Path(p)

    if path.is_file():
        return path
    else:
        return False

def update_files() -> None:
    glob.pfps.update_file()
    glob.beatmaps.update_file()
    glob.profiles.update_file()
    glob.modified_beatmaps.update_file()

async def _add_to_player_queue(packets: bytes) -> None:
    while not glob.player:
        await asyncio.sleep(1)
    
    glob.player.queue += packets

def add_to_player_queue(packets: bytes) -> None:
    """Safe way to add to a player's queue"""
    asyncio.create_task(_add_to_player_queue(packets))

def filter_top_scores(_scores: list[dict]) -> list[dict]:
    """Removes duplicated scores"""
    md5s = []
    scores = []
    for s in _scores:
        if s['md5'] not in md5s:
            md5s.append(s['md5'])
            scores.append(s)

    return scores

def log(*message: str, color: str = Color.WHITE) -> None:
    print(f"{color}{' '.join(message)}")
    return

log_error = lambda *m: log(*m, color = Color.RED)
log_success = lambda *m: log(*m, color = Color.GREEN)

def bytes_to_string(b: bytes) -> str:
    return base64.b64encode(b).decode('ascii')

def string_to_bytes(s: str):
    return base64.b64decode(s.encode('ascii'))

def render_menu(
    channel_name: str, 
    description: str,
    buttons: list[BUTTON]
):
    body = bytearray()
    
    body += packets.userSilenced(-1)
    body += packets.sendMsg(
        client = 'local',
        msg = description,
        target = '#osu',
        userid = -1,
    )

    for url, name in buttons:
        if r'{mode}' in url:
            if glob.mode:
                m = repr(glob.mode).lower()
            else:
                m = 'vn'
            
            url = url.format(
                mode = m
            )
        
        body += packets.sendMsg(
            client = 'local',
            msg = f'[{url} {name}]',
            target = channel_name,
            userid = -1,
        )
    
    add_to_player_queue(body)