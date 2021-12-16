import time
import utils
import config
import orjson
import queries
import packets
from ext import glob
from typing import Union
from typing import Optional

SCORES = list[dict]
RANKED_PLAYS = dict[str, list[dict]]
APPROVED_PLAYS = RANKED_PLAYS
OSU_DAILY_API = 'https://osudaily.net/api'

class Player:
    def __init__(self, name: str) -> None:
        self.name = name
        if name not in glob.profiles:
            self.init_db()
        
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
    
    def init_db(self) -> None:
        if (
            not glob.pfps or
            self.name not in glob.pfps or
            glob.pfps[self.name] is None
        ):
            glob.pfps.update({self.name: None})

        if (
            not glob.profiles or 
            self.name not in glob.profiles
        ):
            glob.profiles.update(
                queries.init_profile(self.name)
            )
        
        utils.update_files()
        glob.current_profile = glob.profiles[self.name]

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
        
        if 'rank' not in json:
            input((
                'Hey!\n'
                'If you have a valid osu!daily api key and end up\n' 
                'Seeing this error please send this to cover on discord!\n'
                f'With the following info: {json}\n'
                '(At this point, set `config.osu_daily_api_key` to `None`)'
            ))
            return 1
            
        return json['rank']
    
    async def update(self) -> None:
        scores: SCORES = []

        if not glob.current_profile:
            glob.current_profile = glob.profiles[self.name]

        ranked_plays: Optional[RANKED_PLAYS] = \
        glob.current_profile['plays']['ranked_plays']

        approved_plays: Optional[APPROVED_PLAYS] = \
        glob.current_profile['plays']['approved_plays']
        
        for plays in (ranked_plays, approved_plays):
            if plays:
                for v in plays.values():
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
        if top_scores:
            self.acc = sum([s['acc'] for s in top_scores]) / len(top_scores)

        all_plays: Optional[SCORES] = \
        glob.current_profile['plays']['all_plays']
        
        if all_plays is not None:
            self.playcount = len(all_plays)
        
        self.rank = await self.get_rank()

        self.queue += packets.userStats(self)