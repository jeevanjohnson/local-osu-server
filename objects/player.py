import time
import utils
import config
import orjson
import packets
from ext import glob
from typing import Union
from typing import Optional

SCORES = list[dict]
RANKED_PLAYS = dict[str, list[dict]]
OSU_DAILY_API = 'https://osudaily.net/api'

class Player:
    def __init__(self) -> None:
        self.name = config.player_name
        self.queue = bytearray()
        self.login_time = time.time()

        # TODO: update/change these eventually
        self.rank: int = 1 # TODO: change depending on pp compared to bancho ranking
        self.acc: float = 100.0
        self.playcount: int = 0 
        self.total_score: int = 0
        self.ranked_score: int = 0
        self.pp: Union[float, int] = 0

        # constants
        self.mode = 0
        self.mods = 0
        self.userid = 2
        self.action = 0
        self.map_id = 0
        self.country = 0
        self.map_md5 = ''
        self.utc_offset = 0
        self.info_text = ''
        self.location = (0.0, 0.0)
        self.bancho_privs = 63
    
    def clear(self) -> bytearray:
        _queue = self.queue.copy()
        self.queue.clear()
        return _queue 

    async def get_rank(self) -> int:
        if config.osu_daily_api_key is None:
            return 1
        
        url = f'{OSU_DAILY_API}/pp.php'
        params = {
            'k': config.osu_daily_api_key,
            't': 'pp',
            'v': self.pp,
            'm': self.mode
        }

        async with glob.http.get(url, params=params) as resp:
            if not resp or resp.status != 200:
                return 1
            
            json = orjson.loads(await resp.content.read())
            if not json:
                return 1
            
        return json['rank']
    
    async def update(self) -> None:
        scores: SCORES = []

        ranked_plays: Optional[RANKED_PLAYS] = \
        glob.current_profile['plays']['ranked_plays']
        
        if ranked_plays:
            for v in ranked_plays.values():
                scores.extend(v)
        
            scores.sort(key = lambda s: s['pp'], reverse = True)
            top_scores = utils.filter_top_scores(scores[:100])
            top_scores.sort(key = lambda s: s['pp'], reverse = True)

            pp = sum([s['pp'] * 0.95 ** i for i, s in enumerate(top_scores)])
            pp += 416.6667 * (1 - (0.9994 ** len(scores)))
            self.pp = round(pp)

            # TODO: figure out how bancho does it
            # for now just get the average acc for all top plays
            # combined
            self.acc = sum([s['acc'] for s in top_scores]) / len(top_scores)

        all_plays: Optional[SCORES] = \
        glob.current_profile['plays']['all_plays']
        
        if all_plays is not None:
            self.playcount = len(all_plays)
        
        self.rank = await self.get_rank()

        self.queue += packets.userStats(self)
        self.queue += packets.userPresence(self)