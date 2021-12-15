PATH_TO_PROFILES = r''
OSU_API_KEY = r''

"""
THIS CODE IS BAD
BUT IT JUST RECALCS ALL PLAYS
"""

OSU_API_BASE = 'https://osu.ppy.sh/api'

import asyncio
import aiohttp
from typing import Any
import pyttanko as oppai
from pathlib import Path
from typing import TypedDict

JsonFile: Any = 0
p = [*Path.cwd().parts, 'objects', 'jsonfile.py']
try: p.remove('scripts')
except: pass
jsonfile = Path('\\'.join(p))
exec(jsonfile.read_text())

class Score(TypedDict):
    mode: int
    md5: str
    name: str
    n300: int
    n100: int
    n50: int
    ngeki: int
    nkatu: int
    nmiss: int
    score: int
    max_combo: int
    perfect: bool
    mods: int
    additional_mods: int
    acc: float
    pp: float
    replay_md5: str
    time: float

file = JsonFile(PATH_TO_PROFILES)

http: aiohttp.ClientSession
parser = oppai.parser()
async def recalc(md5: str, score: Score) -> Score:
    params = {
        'k': OSU_API_KEY,
        'h': md5
    }
    async with http.get(
        url = f'{OSU_API_BASE}/get_beatmaps',
        params = params
    ) as resp:
        if not resp or resp.status != 200:
            score['pp'] = 0.0
            return score
        
        if not (json := await resp.json()):
            score['pp'] = 0.0
            return score
        
        bmap_json: dict = json[0]
    
    url = f'https://osu.ppy.sh/osu/{bmap_json["beatmap_id"]}'
    async with http.get(url) as resp:
        if not resp or resp.status != 200:
            score['pp'] = 0.0
            return score
        
        if not (content := await resp.content.read()):
            score['pp'] = 0.0
            return score
        
        if not content:
            score['pp'] = 0.0
            return score
    
    bmap = parser.map(
        osu_file = content.decode().splitlines()
    )
    
    stars = oppai.diff_calc().calc(bmap, score['mods'])
    pp, *_, acc_percent = oppai.ppv2(
        aim_stars = stars.aim, 
        speed_stars = stars.speed, 
        bmap = bmap, 
        mods = score["mods"],
        n300 = score["n300"],
        n100 = score["n100"], 
        n50 = score["n50"],
        nmiss = score["nmiss"]
    )

    score['pp'] = pp
    score['acc'] = acc_percent
    return score

async def main() -> None:
    global http
    http = aiohttp.ClientSession()

    for ii, profile_name in enumerate(file):
        print(f'{ii}/{len(file)}', 'profiles calculated')
        profile = file[profile_name]
        for idx, map_status in enumerate(('ranked_plays', 'approved_plays')):
            print('calculating', map_status[:-6], f'{idx+1}/2')
            plays = profile['plays'][map_status]
            for i, (md5, map_plays) in enumerate(plays.items()):
                for idx, play in enumerate(map_plays):
                    map_plays[idx] = await recalc(md5, play)
                    print(f'{idx+1}/{len(map_plays)}', 'plays in a map calculated')
            
                print(f'{i+1}/{len(plays.values())}', 'maps calculated')

    await http.close()
    file.update_file()
    print('finished and updated file!')

asyncio.run(main())