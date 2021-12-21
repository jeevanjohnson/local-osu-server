import re
import asyncio
from pathlib import Path
import pyttanko as oppai
from typing import Union
from colorama import Fore
from typing import Literal
from typing import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects import Score
    from objects import Beatmap
    from objects import ModifiedBeatmap

try:
    from ext import glob
except ImportError:
    pass

Color = Fore

PP = float
ACCURACY = float
def calculator(
    score: 'Score', bmap: Union['Beatmap', 'ModifiedBeatmap', oppai.beatmap]
) -> tuple[PP, ACCURACY]:
    """PP calculator (easy to work with and change whenever needed)"""
    if not isinstance(bmap, oppai.beatmap):
        file = bmap.map_file
    else:
        file = bmap
    
    stars = oppai.diff_calc().calc(file, score.mods)
    pp, *_, acc_percent = oppai.ppv2(
        aim_stars = stars.aim, 
        speed_stars = stars.speed, 
        bmap = file, 
        mods = score.mods,
        n300 = score.n300,
        n100 = score.n100, 
        n50 = score.n50,
        nmiss = score.nmiss,
        combo = score.max_combo
    )

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

def log(*message: str, color: str = Color.WHITE):
    print(f"{color}{' '.join(message)}")
    return