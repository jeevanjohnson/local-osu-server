import config
from ext import glob
from typing import Union
from typing import Optional
from objects.score import Score
from objects.beatmap import Beatmap
from objects.score import BanchoScore

ONLINE_PLAYS = dict[str, list[dict]]
OSU_API_BASE = 'https://osu.ppy.sh/api'

status_to_db = {
    1: 'ranked',
    2: 'approved',
    3: 'qualified',
    4: 'loved'
}

"""Map ranking types"""
NOTSUBMITTED = -1
PENDING = 0
UPDATEAVALIABLE = 1
RANKED = 2
APPROVED = 3
QUALIFIED = 4
LOVED = 5

"""Leaderboard types"""
LOCAL   = 0
TOP     = 1
MODS    = 2
FRIENDS = 3
COUNTRY = 4

FROM_API_TO_SERVER_STATUS = {
    4: LOVED,
    3: QUALIFIED,
    2: APPROVED,
    1: RANKED,
    0: PENDING,
    -1: PENDING, # wip
    -2: PENDING  # graveyard
}

STARTING_LB_FORMAT = (
    "{rankedstatus}|false|{mapid}|{setid}|{num_of_scores}\n0\n"
    "[bold:0,size:20]{artist_unicode}|{title_unicode}\n10.0\n"
)
SCORE_FORMAT = (
    "{score_id}|{username}|{score}|"
    "{maxcombo}|{count50}|{count100}|"
    "{count300}|{countmiss}|{countkatu}|"
    "{countgeki}|{perfect}|{enabled_mods}|{user_id}|"
    "{num_on_lb}|{time}|{replay_available}"
)
VALID_LB_STATUESES = (LOVED, QUALIFIED, RANKED, APPROVED)

class Leaderboard:
    def __init__(self) -> None:
        self.personal_score: Optional[Score] = None
        self.scores: list[Union[Score, BanchoScore]] = []
        
        self.bmap: Optional[Beatmap] = None
        # self.bmap: Optional[Union[Beatmap, ModifiedBeatmap]] = None
    
    @property
    def lb_base_fmt(self) -> Optional[bytes]:
        if not self.bmap:
            return
        
        return STARTING_LB_FORMAT.format(
            rankedstatus = FROM_API_TO_SERVER_STATUS[self.bmap.approved],
            mapid = self.bmap.beatmap_id,
            setid = self.bmap.beatmapset_id,
            num_of_scores = len(self.scores),
            artist_unicode = self.bmap.artist_unicode or self.bmap.artist,
            title_unicode = self.bmap.title_unicode or self.bmap.title
        ).encode()

    @property
    def as_binary(self) -> bytes:
        if not self.bmap:
            return b'0|false'
        
        r = FROM_API_TO_SERVER_STATUS[self.bmap.approved]
        if r not in VALID_LB_STATUESES:
            return f'{r}|false'.encode()

        if not self.lb_base_fmt:
            return f'{r}|false'.encode()
        
        buffer = bytearray()
        buffer += self.lb_base_fmt

        if self.personal_score:
            if self.personal_score not in self.scores:
                num_on_lb = 101
            else:
                num_on_lb = self.scores.index(self.personal_score) + 1

            self.personal_score.score = int(self.personal_score.pp or 0)
            buffer += SCORE_FORMAT.format(
                **self.personal_score.as_leaderboard_score,
                num_on_lb = num_on_lb
            ).encode()
            buffer += b'\n'
        else:
            buffer += b'\n'
        
        len_scores = len(self.scores)
        for idx, s in enumerate(self.scores):
            idx += 1
            buffer += SCORE_FORMAT.format(
                **s.as_leaderboard_score,
                num_on_lb = idx
            ).encode()
            if idx != len_scores:
                buffer += b'\n'
        
        return bytes(buffer)
    
    @classmethod
    async def from_offline(
        cls, filename: str, mods: int,
        mode: int, rank_type: int,
        set_id: int, md5: str
    ) -> 'Leaderboard':
        lb = cls()

        bmap = Beatmap()
        bmap.approved = 3
        bmap.title_unicode = bmap.title = ''
        bmap.artist_unicode = bmap.artist = ''
        bmap.beatmap_id = bmap.beatmapset_id = 0
        
        lb.bmap = bmap
        scores: list[Union[Score, BanchoScore]] = []

        lb.scores = scores
        if (
            not glob.player or 
            not glob.current_profile
        ):
            return lb

        key = 'qualified_plays'
        
        _player_scores: Optional[ONLINE_PLAYS] = \
        glob.current_profile['plays'][key]
        
        if not _player_scores:
            return lb
        
        if md5 not in _player_scores:
            return lb

        player_scores = _player_scores[md5]

        player_scores.sort(key = lambda s: s['score'], reverse = True)

        if rank_type == MODS:
            player_scores = [x for x in player_scores if x['mods'] & mods]
            if not player_scores:
                return lb
            
            player_score = Score.from_dict(player_scores[0])
        else:
            player_score = Score.from_dict(player_scores[0])

        lb.scores.append(player_score)
        lb.scores.sort(key = lambda s: int(s.score), reverse = True)
        
        if lb.scores.index(player_score) == 100:
            lb.scores.remove(player_score)
        
        lb.personal_score = player_score

        return lb   

    @classmethod
    async def from_bancho(
        cls, filename: str, mods: int,
        mode: int, rank_type: int,
        set_id: int, md5: str
    ) -> 'Leaderboard':
        lb = cls()

        lb.bmap = bmap = await Beatmap.from_md5(md5)
        if not bmap:
            return lb

        ranked_status = FROM_API_TO_SERVER_STATUS[bmap.approved]
        if ranked_status not in VALID_LB_STATUESES:
            return lb
        
        if config.osu_api_key is not None:
            params = {
                'k': config.osu_api_key,
                'b': bmap.beatmap_id,
                'limit': 100
            }
            if rank_type == MODS:
                params['mods'] = mods
            
            async with glob.http.get(
                url = f'{OSU_API_BASE}/get_scores',
                params = params
            ) as resp:            
                scores: list[Union[Score, BanchoScore]] = [
                    BanchoScore(x) for x in await resp.json()
                ]
        else:
            scores: list[Union[Score, BanchoScore]] = []

        lb.scores = scores
        if (
            not glob.player or 
            not glob.current_profile
        ):
            return lb

        key = f'{status_to_db[bmap.approved]}_plays'
        
        _player_scores: Optional[ONLINE_PLAYS] = \
        glob.current_profile['plays'][key]
        
        if not _player_scores:
            return lb
        
        if md5 not in _player_scores:
            return lb

        player_scores = _player_scores[md5]

        player_scores.sort(key = lambda s: s['score'], reverse = True)

        if rank_type == MODS:
            player_scores = [x for x in player_scores if x['mods'] == mods]
            if not player_scores:
                return lb
            
            player_score = Score.from_dict(player_scores[0])
        else:
            player_score = Score.from_dict(player_scores[0])

        lb.scores.append(player_score)
        lb.scores.sort(key = lambda s: int(s.score), reverse = True)

        if lb.scores.index(player_score) == 100:
            lb.scores.remove(player_score)
        
        lb.personal_score = player_score

        return lb   
    
    """
    @classmethod
    async def from_modified(
        cls, filename: str, mods: int,
        mode: int, rank_type: int,
        set_id: int, md5: str
    ) -> 'Leaderboard':
        lb = cls()

        if not glob.player:
            return lb

        if glob.db.is_in(md5, ['beatmaps']):
           bmap = ModifiedBeatmap.from_db(md5)
        else:
           bmap = await ModifiedBeatmap.from_params(filename, set_id, md5)

        if not bmap:
            return lb

        ranked_status = FROM_API_TO_SERVER_STATUS[bmap.approved]
        if ranked_status not in VALID_LB_STATUESES:
            return lb
        
        if not bmap.in_db:
            bmap.add_to_db()
        
        lb.bmap = bmap

        key = f'{status_to_db[bmap.approved]}_plays'
        path_to_type_plays = ['profiles', glob.player.name, 'plays', key]
        if glob.db.is_in(bmap.file_md5, path_to_type_plays):
            path_to_type_plays.append(bmap.file_md5)
            t = glob.db.search(path_to_type_plays)
            print
        else:
            return lb
        
        #lb.scores = [Score.from_dict(x) for x in ]
    """