import os
import re
import utils
import config
import hashlib
import functools
from ext import glob
from typing import Any
from typing import Union
import pyttanko as oppai
from pathlib import Path
import glob as builtin_glob
from typing import Optional

parser = oppai.parser()

BMAP_DICT = dict[str, Any]
OSU_API_BASE = 'https://osu.ppy.sh/api'

def real_type(value: str) -> Union[float, int, str]:
    if not isinstance(value, str):
        return value
    
    if value.replace('-', '', 1).isdecimal():
        return int(value)
    
    try: return float(value)
    except: pass

    return value

class Beatmap:
    def __init__(self) -> None:
        self.beatmapset_id: int
        self.beatmap_id: int
        self.approved: int
        self.total_length: int
        self.hit_length: int
        self.version: str
        self.file_md5: str
        self.diff_size: float
        self.diff_overall: float
        self.diff_approach: float
        self.diff_drain: float
        self.mode: int
        self.count_normal: int
        self.count_slider: int
        self.count_spinner: int
        self.submit_date: str
        self.approved_date: Optional[str]
        self.last_update: str
        self.artist: str
        self.artist_unicode: str
        self.title: str
        self.title_unicode: str
        self.creator: str
        self.creator_id: int
        self.bpm: float
        self.source: str
        self.tags: str
        self.genre_id: int
        self.language_id: int
        self.favourite_count: int
        self.rating: int
        self.storyboard: int
        self.video: int
        self.download_unavaliable: int
        self.audio_unavailable: int
        self.playcount: int
        self.passcount: int
        self.packs: str
        self.max_combo: int
        self.diff_aim: float
        self.diff_speed: float
        self.difficultyrating: float
        self.file_content: bytes
    
    def as_dict(self) -> dict:
        bmap = self.__dict__.copy()
        if 'file_content' in self.__dict__:
            bmap['file_content'] = f"{bmap['file_content']}"
       
        try: del bmap['map_file']
        except: pass
        
        return bmap

    @functools.cached_property
    def map_file(self) -> oppai.beatmap:
        return parser.map(
            osu_file = self.file_content.decode().splitlines()
        )
    
    async def get_file(self) -> Optional[bytes]:
        if 'file_content' in self.__dict__:
            return self.file_content
        
        url = f'https://osu.ppy.sh/osu/{self.beatmap_id}'
        async with glob.http.get(url) as resp:
            if not resp or resp.status != 200:
                return
            
            if not (content := await resp.content.read()):
                return
            
            self.file_content = content
            return content

    @property
    def in_db(self) -> bool:
        return self.file_md5 in glob.beatmaps

    def add_to_db(self) -> None:
        glob.beatmaps[self.file_md5] = self.as_dict()
        utils.update_files()

    @classmethod
    def from_db(cls, md5: str) -> Optional['Beatmap']:
        bmap_dict: Optional[BMAP_DICT] = glob.beatmaps[md5]
        if not bmap_dict:
            return
        
        bmap_dict = bmap_dict.copy()

        if 'file_content' in bmap_dict:
            exec(f'def get_bytes(): return {bmap_dict["file_content"]}')
            bmap_dict['file_content'] = locals()['get_bytes']()
        
        bmap = cls()
        for k, v in bmap_dict.items():
            bmap.__dict__[k] = v

        return bmap

    @classmethod
    async def from_md5(cls, md5: str) -> Optional['Beatmap']:
        if md5 in glob.beatmaps:
            return cls.from_db(md5)
        
        if config.osu_api_key is None:
            return None

        params = {
            'k': config.osu_api_key,
            'h': md5
        }
        async with glob.http.get(
            url = f'{OSU_API_BASE}/get_beatmaps',
            params = params
        ) as resp:
            if not resp or resp.status != 200:
                return
            
            if not (json := await resp.json()):
                return
            
            bmap_json: dict = json[0]
        
        bmap = cls()
        for k, v in bmap_json.items():
            bmap.__dict__[k] = real_type(v)
        
        return bmap

"""
FILENAME_PARSER = re.compile(r"(?P<artist>.*) - (?P<song_name>.*) ((?P<mapper>.*) \[)(?P<diff_name>.*)\]\.osu")
class ModifiedBeatmap(Beatmap):
    def __init__(self) -> None:
        self.path: Optional[str] = None
        self.original_map: Optional[Beatmap] = None
        super().__init__()
    
    @classmethod
    def from_db(cls, md5: str) -> Optional['ModifiedBeatmap']:
        bmap = cls()
        m = glob.db.search(('beatmaps', md5))
        print

    @classmethod
    async def from_params(cls, filename: str, set_id: int, md5: str) -> Optional['ModifiedBeatmap']:
        mbmap = cls()

        if not (name_data := FILENAME_PARSER.search(filename)):
            return

        if set_id > 0:
            check = f'{glob.songs_folder}\\{set_id}*'
        else:
            check = f'{glob.songs_folder}\\* {name_data["artist"]} - {name_data["song_name"]}*'
        
        paths = builtin_glob.iglob(check, recursive=True)
        if not paths:
            return 
        
        for folder_path in paths:
            original_file: Optional[Path] = None
            for fname in os.listdir(folder_path):
                if not fname.endswith('.osu'):
                    continue
                
                _fname = fname[:-5]
                if (
                    _fname.lower() in filename.lower() and 
                    filename.lower() != fname.lower()
                ):
                    original_file = Path(folder_path) / fname
                    break
            
            if original_file:
                break
        
        if not original_file:
            return
        
        modifiedmap = (Path(folder_path) / filename) # type: ignore
        original_md5 = hashlib.md5(original_file.read_bytes()).hexdigest()
        bmap = await cls.from_md5(original_md5)
        if not bmap:
            return
        
        bmap.file_md5 = md5
        for k, v in bmap.as_dict().items():
            mbmap.__dict__[k] = real_type(v)

        mbmap.path = str(modifiedmap) # type: ignore
        mbmap.file_content = modifiedmap.read_bytes()
        return mbmap
"""