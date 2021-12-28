import time
import utils
import config
from ext import glob
from typing import Union
from typing import Optional
from objects.mods import Mods
from objects.score import Score
from constants import ParsedParams
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

LB_NOT_SUPPORTED_PLACEHOLDER =  Score(
    0, '', "Not supported atm!", 
    0, 0, 0, 0, 0, 0, 0, 0, False, 0, int(time.time())
)
BLANK_BMAP = Beatmap(
    approved = 3,
    title_unicode = '',
    title = '',
    artist_unicode = '',
    artist = '',
    beatmap_id = 0,
    beatmapset_id = 0
)

SCORE = Union[Score, BanchoScore]
class Leaderboard:
    def __init__(self) -> None:
        self.scores: list[SCORE] = []
        self.bmap: Optional[Beatmap] = None
        self.personal_score: Optional[Score] = None

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
                num_on_lb = config.amount_of_scores_on_lb + 1
            else:
                num_on_lb = self.scores.index(self.personal_score) + 1
            
            buffer += SCORE_FORMAT.format(
                **self.personal_score.as_leaderboard_score,
                num_on_lb = num_on_lb
            ).encode()
            buffer += b'\n'
        else:
            buffer += b'\n'

        len_scores = len(self.scores)
        enabled = None
        for idx, s in enumerate(self.scores):
            idx += 1
            
            if idx == 1:
                if config.show_pp_for_personal_best:
                    enabled = True
                    config.show_pp_for_personal_best = False
                else:
                    enabled = False
            
            buffer += SCORE_FORMAT.format(
                **s.as_leaderboard_score,
                num_on_lb = idx
            ).encode()
            if idx != len_scores:
                buffer += b'\n'
        
        if enabled:
            config.show_pp_for_personal_best = True

        return bytes(buffer)

    @classmethod
    async def from_offline(
        cls, client_params: ParsedParams
    ) -> 'Leaderboard':
        lb = cls()
        md5 = client_params['md5']
        mods = client_params['mods']
        rank_type = client_params['rank_type']

        lb.bmap = BLANK_BMAP
        scores: list[Union[Score, BanchoScore]] = []

        lb.scores = scores
        if (
            not glob.player or
            not glob.current_profile
        ):
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        key = 'qualified_plays'

        _player_scores: Optional[ONLINE_PLAYS] = \
        glob.current_profile['plays'][key]

        if not _player_scores:
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        if md5 not in _player_scores:
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        player_scores = _player_scores[md5].copy()

        if glob.mode:
            player_scores = [x for x in player_scores if x['mods'] & glob.mode]
        else:
            player_scores = [
                x for x in player_scores if
                not x['mods'] & (Mods.RELAX | Mods.AUTOPILOT)
            ]

        if config.pp_leaderboard or glob.mode:
            player_scores.sort(key = lambda s: s['pp'], reverse = True)
        else:
            player_scores.sort(key = lambda s: s['score'], reverse = True)

        if rank_type == MODS:
            player_scores = [x for x in player_scores if x['mods'] & mods]
            if not player_scores:
                lb.scores = lb.scores[:config.amount_of_scores_on_lb]
                return lb

            player_score = Score.from_dict(player_scores[0])
        else:
            player_score = Score.from_dict(player_scores[0])

        lb.scores.append(player_score)

        if config.pp_leaderboard:
            lb.scores.sort(
                key = lambda s: int(s.pp), # type: ignore
                reverse = True
            )
        else:
            lb.scores.sort(
                key = lambda s: int(s.score),
                reverse = True
            )

        if lb.scores.index(player_score) == 100:
            lb.scores.remove(player_score)

        lb.personal_score = player_score
        lb.scores = lb.scores[:config.amount_of_scores_on_lb]
        return lb

    @classmethod
    async def from_bancho(
        cls, client_params: ParsedParams
    ) -> 'Leaderboard':
        lb = cls()
        md5 = client_params['md5']
        mods = client_params['mods']
        rank_type = client_params['rank_type']

        lb.bmap = bmap = await Beatmap.from_md5(md5)
        if not bmap:
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        ranked_status = FROM_API_TO_SERVER_STATUS[bmap.approved]
        if ranked_status not in VALID_LB_STATUESES:
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        if config.osu_api_key:
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
                scores: list[SCORE] = [
                    BanchoScore(x) for x in await resp.json()
                ]
        else:
            scores: list[SCORE] = []

        if config.pp_leaderboard:
            await bmap.get_file()
            scores.sort(
                key = lambda s: utils.calculator(s, bmap)[0],
                reverse = True
            )

        lb.scores = scores
        if (
            not glob.player or
            not glob.current_profile
        ):
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        key = f'{status_to_db[bmap.approved]}_plays'

        _player_scores: Optional[ONLINE_PLAYS] = \
        glob.current_profile['plays'][key]

        if not _player_scores:
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        if md5 not in _player_scores:
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        player_scores = _player_scores[md5]
        if glob.mode:
            player_scores = [
                x for x in player_scores if x['mods'] & glob.mode
            ]
        else:
            player_scores = [
                x for x in player_scores if
                not x['mods'] & (Mods.RELAX | Mods.AUTOPILOT)
            ]

        if not player_scores:
            lb.scores = lb.scores[:config.amount_of_scores_on_lb]
            return lb

        if config.pp_leaderboard or glob.mode:
            player_scores.sort(key = lambda s: s['pp'], reverse = True)
        else:
            player_scores.sort(key = lambda s: s['score'], reverse = True)

        if rank_type == MODS:
            player_scores = [x for x in player_scores if x['mods'] == mods]
            if not player_scores:
                lb.scores = lb.scores[:config.amount_of_scores_on_lb]
                return lb

            player_score = Score.from_dict(player_scores[0])
        else:
            player_score = Score.from_dict(player_scores[0])

        lb.scores.append(player_score)

        if config.pp_leaderboard:
            lb.scores.sort(
                key = lambda s: int(s.pp), # type: ignore
                reverse = True
            )
        else:
            lb.scores.sort(
                key = lambda s: int(s.score),
                reverse = True
            )

        if lb.scores.index(player_score) == 100:
            lb.scores.remove(player_score)

        lb.personal_score = player_score
        lb.scores = lb.scores[:config.amount_of_scores_on_lb]
        return lb

class NotSupported(Leaderboard):
    def __init__(self) -> None:
        super().__init__()
        self.bmap = BLANK_BMAP
        self.scores.append(LB_NOT_SUPPORTED_PLACEHOLDER)