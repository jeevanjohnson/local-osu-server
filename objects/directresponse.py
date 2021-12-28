import time
import utils
from typing import Union
from typing import Optional
from typing import TypedDict
from datetime import datetime

DIRECT_DIFF_FORMAT = (
    '[{difficulty:.2f}⭐] {version} {{CS{cs} OD{accuracy} AR{ar} HP{drain}}}@{mode_int}'
)

DIRECT_SET_FORMAT = (
    '{id}.osz|{artist}|{title}|{creator}|'
    '{ranked}|10.0|{last_updated}|{id}|'
    '0|0|0|0|0|{diffs}' 
    # 0s are threadid, has_vid, has_story, filesize, filesize_novid
)

PLAY_FORMAT = (
    '{title} [{version}]'
    ' {pp:.0f}PP +{mods_str} {acc:.2f}% {grade} '
    '{max_combo}x/{bmap_max_combo}x {nmiss}X'
)

class BeatmapDiff(TypedDict):
    difficulty: float
    version: str
    cs: float
    accuracy: float
    ar: float
    drain: float
    mode_int: int

class BeatmapSet(TypedDict):
    id: int # setid
    artist: str
    title: str
    creator: str
    ranked: int
    last_updated: str # utc timestamp
    beatmaps: list[Union[BeatmapDiff, str]]

class DirectResponse:
    """Sends certain messages and such as an osu! direct response"""
    def __init__(
        self, bmaps: Optional[list[BeatmapSet]] = None
    ) -> None:
        if bmaps:
            self.bmaps = bmaps
        else:
            self.bmaps = []

    def __bytes__(self) -> bytes:
        return self.as_binary

    @property
    def as_binary(self) -> bytes:
        len_maps = len(self.bmaps)
        bmaps = [f"{'101' if len_maps == 100 else len_maps}"]

        for bmap in self.bmaps:
            diffs = []
            beatmaps = bmap['beatmaps']
            if beatmaps and isinstance(beatmaps[0], str):
                m = beatmaps[0]
                diffs.append(
                    f"{m}@0" if '@' not in m else m
                )
            else:
                for row in sorted(
                    beatmaps, key = lambda x: x['difficulty'] # type: ignore
                ):
                    diffs.append(
                        DIRECT_DIFF_FORMAT.format(**row) # type: ignore
                    )

            diffs = ','.join(diffs)
            bmaps.append(DIRECT_SET_FORMAT.format(**bmap, diffs=diffs))
        
        return '\n'.join(bmaps).encode()
    
    def load_fake_bmap(
        self, id: int, message: str
    ) -> BeatmapSet:
        utctime = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        fake_bmap_set = BeatmapSet(
            id = id,
            artist = message,
            title = '',
            creator = '',
            ranked = 1,
            last_updated = utctime,
            beatmaps = ['']
        )

        return fake_bmap_set

    def send_normal_message(
        self, message: str, 
        start_id: int = -1
    ) -> None:
        """adds a message to the direct response"""
        split = message.splitlines()

        for line in split:
            fake_id = start_id if not self.bmaps else -len(self.bmaps)
            
            self.bmaps.append(
                self.load_fake_bmap(fake_id, message=line)
            )

    @classmethod
    def from_str(cls, s: str, start_id: int = -2) -> 'DirectResponse':
        resp = cls()
        resp.send_normal_message(s, start_id=start_id)
        return resp
    
    @classmethod
    def from_plays(cls, plays: list[dict]) -> 'DirectResponse':
        resp = cls()
        for idx, play in enumerate(plays):
            if not play['bmap']:
                continue
        
            if 'original_bmap' in play['bmap']:
                bmap = play['bmap']['original_bmap']
                version = play['bmap']['version']
            else:
                bmap = play['bmap']
                version = bmap['version']

            if 'setid' in play['bmap']:
                setid = play['bmap']['setid']
            else:
                setid = play['bmap']['beatmapset_id']

            play_grade = utils.get_grade(
                n300 = play['n300'],
                n100 = play['n100'],
                n50 = play['n50'],
                nmiss = play['nmiss'],
                mods = play['mods']
            )

            title = PLAY_FORMAT.format(
                title = bmap['title'],
                version = version,
                mods_str = play['mods_str'],
                acc = play['acc'],
                grade = play_grade,
                pp = play['pp'],
                max_combo = play['max_combo'],
                bmap_max_combo = bmap['max_combo'],
                nmiss = play['nmiss']
            )

            if len(title) > 100:
                title = f"{title[:90]}..."
            
            diff_version = (
                f"{play['pp']:.0f}PP +{play['mods_str']} "
                f"{play['acc']:.2f}% {play_grade} "
                f"{play['max_combo']}x/{bmap['max_combo']}x {play['nmiss']}X"
                f"@{play['mode']}"
            )

            utc_play_time_str = time.strftime(
                '%Y-%m-%dT%H:%M:%SZ', 
                time.localtime(play['time'])
            )

            fake_set = BeatmapSet(
                id = -setid,
                artist = f"{idx+1}. {bmap['artist']}",
                title = title,
                creator = bmap['creator'],
                ranked = bmap['approved'],
                last_updated = utc_play_time_str,
                beatmaps = [diff_version]
            )

            resp.bmaps.append(fake_set)
    
        return resp