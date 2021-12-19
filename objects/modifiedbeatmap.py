import utils
import functools
from ext import glob
from pathlib import Path
import pyttanko as oppai
from typing import Optional
from typing import TypedDict
from objects.beatmap import Beatmap

parser = oppai.parser()

class Params(TypedDict):
    filename: str
    mods: int
    mode: int
    rank_type: int
    set_id: int
    md5: str

class ModifiedBeatmap:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(**kwargs)

        self.id: int
        self.md5: str
        self.setid: int
        self.title: str
        self.artist: str
        self.version: str
        self.max_combo: int
        self.file_path: Path
        self.rank_status: int
        self.file_content: bytes
        self.title_unicode: Optional[str]
        self.artist_unicode: Optional[str]
    
    @functools.cached_property
    def map_file(self) -> oppai.beatmap:
        return parser.map(
            osu_file = self.file_content.decode().splitlines()
        )

    @property
    def in_db(self) -> bool:
        return self.md5 in glob.modified_beatmaps

    @property
    def beatmap_id(self) -> int:
        return self.id
    
    @property
    def beatmapset_id(self) -> int:
        return self.setid

    @property
    def file_md5(self) -> str:
        return self.md5

    @property
    def approved(self) -> int:
        return self.rank_status
    
    async def get_file(self) -> bytes:
        return self.file_content
    
    @classmethod
    async def from_md5(cls, md5: str) -> Optional['ModifiedBeatmap']:
        if md5 not in glob.modified_beatmaps:
            return
        
        bmap_dict = glob.modified_beatmaps[md5].copy()

        exec(f'def get_bytes(): return {bmap_dict["file_content"]}')
        bmap_dict['file_content'] = locals()['get_bytes']()

        bmap_dict['file_path'] = Path(bmap_dict['file_path'])

        return cls(**bmap_dict)
    
    @staticmethod
    def add_to_db(bmap: Beatmap, params: Params, path_to_modified: Path) -> None:
        if (md5 := params['md5']) in glob.modified_beatmaps:
            return

        lower_filename = params['filename'].lower()
        url_parsed =  ''.join([
            x.lower() for x in bmap.version 
            if x.isalpha() or x == ' '
        ])
        split = lower_filename.split(url_parsed)        
        version = f"[{bmap.version}{split[-1][:-4]}"
        
        glob.modified_beatmaps[md5] = {
            'md5': md5,
            'rank_status': bmap.approved,
            'id': bmap.beatmap_id,
            'setid': bmap.beatmapset_id,
            'title': bmap.title,
            'artist': bmap.artist,
            'title_unicode': bmap.title_unicode,
            'artist_unicode': bmap.artist_unicode,
            'file_path': str(path_to_modified),
            'file_content': f'{path_to_modified.read_bytes()}',
            'max_combo': bmap.max_combo,
            'version': version
        }

        utils.update_files()