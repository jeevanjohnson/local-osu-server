import os
import time
import utils
import config
import calendar
import binascii
from ext import glob
from typing import Any
from typing import Union
from pathlib import Path
from typing import Optional
from datetime import datetime
from objects.mods import Mods
from objects.replay import Replay
from objects.beatmap import Beatmap
from objects.modifiedbeatmap import ModifiedBeatmap

BEATMAP = Union[Beatmap, ModifiedBeatmap]

class BanchoScore:
    def __init__(
        self, bancho_score: dict[str, str],
        bmap: Optional[Beatmap] = None
    ) -> None:
        self.score_id = bancho_score['score_id']
        self.username = bancho_score['username']
        self.score = bancho_score['score']
        self.maxcombo = bancho_score['maxcombo']
        self.count50 = bancho_score['count50']
        self.count100 = bancho_score['count100']
        self.count300 = bancho_score['count300']
        self.countmiss = bancho_score['countmiss']
        self.countkatu = bancho_score['countkatu']
        self.countgeki = bancho_score['countgeki']
        self.perfect = bancho_score['perfect']
        self.enabled_mods = bancho_score['enabled_mods']
        self.user_id = bancho_score['user_id']
        self.time = calendar.timegm(
            datetime.strptime(bancho_score['date'], "%Y-%m-%d %H:%M:%S").utctimetuple()
        )
        self.replay_available = bancho_score['replay_available']

        self.bmap = bmap
        self.pp: Optional[float] = None

    @property
    def as_leaderboard_score(self) -> dict:
        _dict = self.__dict__.copy()

        _dict['score'] = (
            f"{_dict['pp']:.0f}"
            if config.pp_leaderboard and _dict['pp'] else
            _dict['score']
        )

        _dict = utils.delete_keys(
            _dict, 'pp', 'bmap'
        )

        return _dict

class Score:
    def __init__(
        self, mode: int,
        md5: str, name: str,
        n300: int,  n100: int,
        n50: int, ngeki: int,
        nkatu: int, nmiss: int,
        score: int, max_combo: int,
        perfect: bool, mods: int, time: int,
        replay: Optional[Replay] = None,
        additional_mods: Optional[int] = None,
        bmap: Optional[BEATMAP] = None,
        acc: Optional[float] = None, pp: Optional[float] = None,
        replay_md5: Optional[str] = None, scoreid: Optional[int] = None,
        replay_frames: Optional[bytes] = None, mods_str: Optional[str] = None
    ) -> None:
        self.mode = mode
        self.md5 = md5
        self.name = name
        self.n300 = n300
        self.n100 = n100
        self.n50 = n50
        self.ngeki = ngeki
        self.nkatu = nkatu
        self.nmiss = nmiss
        self.score = score
        self.max_combo = max_combo
        self.perfect = perfect
        self.mods = mods
        self.additional_mods = additional_mods
        self.replay = replay
        self.bmap = bmap
        self.acc = acc
        self.pp = pp
        self.replay_md5 = replay_md5
        self.time = time
        self.scoreid = scoreid
        self.replay_frames = replay_frames
        self.mods_str = mods_str

    def as_dict(self) -> dict[str, Any]:
        score = utils.delete_keys(
            self.__dict__.copy(), 'replay', 'bmap'
        )

        if (
            self.replay_frames and
            isinstance(self.replay_frames, bytes)
        ):
            score['replay_frames'] = utils.bytes_to_string(
                score['replay_frames']
            )

        return score

    @property
    def is_failed(self) -> bool:
        # if has certain mods were u don't fail
        if self.mods & (Mods.RELAX | Mods.AUTOPILOT | Mods.NOFAIL):
            return False

        for lifebar in self.replay.bar_graph: # type: ignore
            if lifebar.current_hp == 0.0:
                return True

        return False

    @classmethod
    def from_dict(
        cls, _dict: dict,
        ignore_binascii_errors: bool = False
    ) -> 'Score':
        dictionary = _dict.copy()

        if 'time' not in dictionary:
            dictionary['time'] = time.time()

        if (
            'replay_frames' in dictionary and
            dictionary['replay_frames']
        ):
            if "b\'" == dictionary['replay_frames'][:2]:
                dictionary['replay_frames'] = eval(dictionary["replay_frames"])
            else:
                if not ignore_binascii_errors:
                    dictionary['replay_frames'] = utils.string_to_bytes(
                        dictionary['replay_frames']
                    )
                else:
                    try:
                        dictionary['replay_frames'] = utils.string_to_bytes(
                            dictionary['replay_frames']
                        )
                    except binascii.Error:
                        pass

        return Score(**dictionary)

    @classmethod
    def from_replay(cls, replay: Path) -> 'Score':
        parsed_replay = Replay.from_file(replay)

        return Score(
            mode = parsed_replay.mode,
            md5 = parsed_replay.beatmap_md5,
            name = parsed_replay.player_name,
            n300 = parsed_replay.n300,
            n100 = parsed_replay.n100,
            n50 = parsed_replay.n50,
            ngeki = parsed_replay.ngeki,
            nkatu = parsed_replay.nkatu,
            nmiss = parsed_replay.nmiss,
            score = parsed_replay.total_score,
            max_combo = parsed_replay.combo,
            perfect = parsed_replay.perfect,
            mods = parsed_replay.mods,
            time = int(time.time()),
            replay_md5 = parsed_replay.replay_md5,
            replay_frames = parsed_replay.raw_frames,
            mods_str = repr(parsed_replay.mods),
            replay = parsed_replay
        )

    @classmethod
    def from_score_sub(cls) -> Optional['Score']:
        if (
            not glob.player or
            not glob.replay_folder
        ):
            return

        files = glob.replay_folder.glob('*.osr')
        replay_path = glob.replay_folder / max(files , key=os.path.getctime)
        replay = Replay.from_file(replay_path)

        s = cls(
            glob.player.mode, replay.beatmap_md5, replay.player_name, # type: ignore
            replay.n300, replay.n100, replay.n50, replay.geki, # type: ignore
            replay.katu, replay.miss, replay.total_score, # type: ignore
            replay.combo, bool(replay.perfect), int(replay.mods), # type: ignore
            int(time.time()), replay, int(replay.additional_mods or 0),
            replay_md5 = replay.replay_md5, # type: ignore
            replay_frames = replay.raw_frames # type: ignore
        )

        return s

    @property
    def as_leaderboard_score(self) -> dict:
        if self.scoreid and self.replay_frames:
            sid = -self.scoreid
        else:
            sid = 0

        pp_checks = (
            config.pp_leaderboard or 
            glob.mode or 
            config.show_pp_for_personal_best
        )

        return {
            'score_id': sid,
            'username': self.name,
            'score': int(self.pp or 0) if pp_checks else self.score,
            'maxcombo': self.max_combo,
            'count50': self.n50,
            'count100': self.n100,
            'count300': self.n300,
            'countmiss': self.nmiss,
            'countkatu': self.nkatu,
            'countgeki': self.ngeki,
            'perfect': int(self.perfect),
            'enabled_mods': self.mods,
            'user_id': 2,
            'time': self.time,
            'replay_available': 1 if sid != 0 else 0
        }