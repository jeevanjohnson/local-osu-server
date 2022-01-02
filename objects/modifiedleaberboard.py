from ext import glob
from typing import Union
from typing import Optional
from utils import log_error
from objects.mods import Mods
from objects.score import Score
from constants import ParsedParams
from objects.beatmap import Beatmap
from objects.modifiedfinder import ModifiedFinder
from objects.modifiedbeatmap import ModifiedBeatmap

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

BMAPID_OR_MD5 = Union[int, str]
BEATMAP = Union[Beatmap, ModifiedBeatmap]
class ModifiedLeaderboard:
    def __init__(self) -> None:
        self.scores: list[Score] = []
        self.bmap: Optional[BEATMAP] = None
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
                num_on_lb = 1
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
                if glob.config.show_pp_for_personal_best:
                    enabled = True
                    glob.config.show_pp_for_personal_best = False
                else:
                    enabled = False
            
            s.name = f'({idx}) {s.name}'
            buffer += SCORE_FORMAT.format(
                **s.as_leaderboard_score,
                num_on_lb = idx
            ).encode()
            if idx != len_scores:
                buffer += b'\n'
        
        if enabled:
            glob.config.show_pp_for_personal_best = True

        return bytes(buffer)

    @classmethod
    async def from_client(
        cls, params: ParsedParams
    ) -> 'ModifiedLeaderboard':
        lb = cls()

        if params['md5'] not in glob.modified_beatmaps:
            finder = ModifiedFinder(
                params['md5'],
                params['filename'],
                params['set_id'],
                params['name_data']
            )

            md5_or_id: Optional[BMAPID_OR_MD5] = None
            funorange_map = await finder.modified_txt_search()
            if funorange_map:
                md5_or_id = finder.get_bmap_id()

            if not funorange_map or not md5_or_id:
                md5_or_id = finder.get_original_md5()
                funorange_map = finder.funorange_map_path

            if (
                not funorange_map or
                not md5_or_id
            ):
                lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
                return lb

            if isinstance(md5_or_id, int):
                bmap = await Beatmap.from_id(md5_or_id)
            else:
                bmap = await Beatmap.from_md5(md5_or_id)

            if not bmap:
                lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
                return lb

            similarity = await finder.origin_edited_similarity(bmap)
            
            # TODO: find a better percentages
            # checks if they aren't similar or
            # they are the same map
            if (
                similarity < 94.5 or
                similarity > 99.975
            ):
                log_error((
                    f'when comparing, similarity was under 94.5% or above 99.975% ({similarity}%)\n'
                    'if you believe this was a mistake or an error, please report it to\n'
                    'cover on discord!'
                ))
                lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
                return lb
            
            if not finder.same_circles():
                log_error('circles in the maps are different!')
                lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
                return lb
            
            lb.bmap = bmap = ModifiedBeatmap.add_to_db(
                bmap, params, funorange_map,
                return_modified = True
            )

            if not bmap:
                lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
                return lb

        else:
            lb.bmap = bmap = await ModifiedBeatmap.from_md5(params['md5'])
            if not bmap:
                lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
                return lb

        ranked_status = FROM_API_TO_SERVER_STATUS[bmap.approved]
        if ranked_status not in VALID_LB_STATUESES:
            lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
            return lb

        if (
            not glob.player or
            not glob.current_profile
        ):
            lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
            return lb

        key = f'{status_to_db[bmap.approved]}_plays'

        _player_scores: Optional[ONLINE_PLAYS] = \
        glob.current_profile['plays'][key]

        if not _player_scores:
            lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
            return lb

        if bmap.file_md5 not in _player_scores:
            lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
            return lb

        player_scores = _player_scores[bmap.file_md5]

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
            lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
            return lb

        if glob.config.pp_leaderboard or glob.mode:
            player_scores.sort(key = lambda s: s['pp'], reverse = True)
        else:
            player_scores.sort(key = lambda s: s['score'], reverse = True)

        if params['rank_type'] == MODS:
            player_scores = [
                x for x in player_scores if
                x['mods'] == params['mods']
            ]
            if not player_scores:
                lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
                return lb

        lb.personal_score = Score.from_dict(player_scores[0])
        lb.scores = [Score.from_dict(x) for x in player_scores]
        lb.scores = lb.scores[:glob.config.amount_of_scores_on_lb]
        return lb