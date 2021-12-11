import re
import asyncio
from ext import glob
from typing import Union
from pathlib import Path
from typing import Literal
from typing import Callable

def handler(target: Union[str, re.Pattern]) -> Callable:
    def inner(func: Callable) -> Callable:
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
    glob.beatmaps.update_file()
    glob.profiles.update_file()
    glob.pfps.update_file()

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