import re
import base64
import asyncio
import colorama
import pyttanko as oppai
from typing import Union
from pathlib import Path
from colorama import Fore
from typing import Literal
from typing import Optional
from typing import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects import Score
    from objects import Beatmap
    from objects import BanchoScore
    from objects import ModifiedBeatmap

try:
    import packets
except ImportError:
    pass

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

def string_to_bytes(s: str) -> bytes:
    return base64.b64decode(s.encode('ascii'))

async def str_to_wslpath(path: str) -> Path:
    wslpath_proc = await asyncio.subprocess.create_subprocess_exec(
        'wslpath', path,
        stdin = asyncio.subprocess.DEVNULL,
        stdout = asyncio.subprocess.PIPE,
        stderr = asyncio.subprocess.DEVNULL,
    )
    stdin, _ = await wslpath_proc.communicate()

    return Path(stdin.decode().removesuffix('\n'))

def delete_keys(_dict: dict, *keys: str) -> dict:
    _dict_copy = _dict.copy()
    for k in keys:
        try: del _dict_copy[k]
        except: pass

    return _dict_copy

def local_message(
    message: str, 
    channel: str = '#osu'
) -> bytes:
    return packets.sendMsg(
        client = 'local',
        msg = message,
        target = channel,
        userid = -1,
    )

def get_grade(
    score: Optional['Score'] = None, 
    n300: Optional[int] = None,
    n100: Optional[int] = None,
    n50: Optional[int] = None,
    nmiss: Optional[int] = None,
    mods: Optional[int] = None
    ) -> str:
    if score:
        total = score.n300 + score.n100 + score.n50 + score.nmiss
        n300_percent = score.n300 / total
        using_hdfl = score.mods & 1032
        nomiss = score.nmiss == 0
        n50 = score.n50
    else:
        total = n300 + n100 + n50 + nmiss # type: ignore
        n300_percent = n300 / total
        using_hdfl = mods & 1032 # type: ignore
        nomiss = nmiss == 0
        n50 = n50

    if n300_percent > 0.9:
        if nomiss and (n50 / total) < 0.1: # type: ignore
            return 'SH' if using_hdfl else 'S'
        else:
            return 'A'

    if n300_percent > 0.8:
        return 'A' if nomiss else 'B'

    if n300_percent > 0.7:
        return 'B' if nomiss else 'C'

    if n300_percent > 0.6:
        return 'C'

    return 'D'