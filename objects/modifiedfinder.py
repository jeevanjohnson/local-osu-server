import re
import os
import utils
import hashlib
from ext import glob
from pathlib import Path
from typing import Union
from typing import Optional
import urllib.parse as urlparse

MD5 = str
BMAPID = int
FUNORANGE_MAP = Path
MD5_OR_BMAPID = Union[MD5, BMAPID]

class ModifiedFinder:
    """Used to find data for funorange maps"""

    def __init__(
        self, md5: str,
        filename: str,
        set_id: int,
        name_data: Optional[re.Match] = None
    ) -> None:
        self.md5 = md5
        self.set_id = set_id
        self.filename = filename
        self.name_data = name_data

        self.funorange_map_path: Optional[FUNORANGE_MAP] = None
        self.original_md5_or_bmapid: Optional[MD5_OR_BMAPID] = None

    def get_original_md5(self) -> Optional[MD5]:
        md5 = None

        path_exists = (
            self.funorange_map_path and
            self.funorange_map_path.exists()
        )

        if not path_exists and glob.songs_folder:
            if self.set_id > 0:
                pattern = f'{self.set_id}*'
                folders = glob.songs_folder.glob(pattern)
            elif self.name_data:
                pattern = f'* {self.name_data["artist"]} - {self.name_data["song_name"]}*'
                folders = glob.songs_folder.glob(pattern)
            else:
                folders = []
        elif self.funorange_map_path:
            folders = (self.funorange_map_path.parent,)
        else:
            folders = []

        lower_filename = self.filename.lower()

        for map_set_folder in folders:
            for map_file in os.listdir(str(map_set_folder)):
                if (
                    self.original_md5_or_bmapid and
                    self.funorange_map_path
                ):
                    break

                if not map_file.endswith('.osu'):
                    continue

                map_file_unquote = urlparse.unquote_plus(map_file)
                lower_map_file_unquote = map_file_unquote.lower()

                if lower_filename == lower_map_file_unquote:
                    self.funorange_map_path = map_set_folder / map_file
                    continue

                if (
                    lower_map_file_unquote[:-5] in lower_filename and
                    lower_filename != lower_map_file_unquote
                ):
                    orignal_bmap_file = map_set_folder / map_file
                    self.original_md5_or_bmapid = md5 = (
                        hashlib.md5(orignal_bmap_file.read_bytes()).hexdigest()
                    )

            if (
                self.original_md5_or_bmapid and
                self.funorange_map_path
            ):
                break

        path_exists = (
            self.funorange_map_path and
            self.funorange_map_path.exists()
        )

        if (
            not self.original_md5_or_bmapid or
            not path_exists
        ):
            return

        return md5

    def get_bmap_id(self) -> Optional[BMAPID]:
        if (
            not self.funorange_map_path or
            not self.funorange_map_path.exists()
        ):
            return

        file_content = self.funorange_map_path.read_bytes().decode(
            errors='ignore'
        ).lower().splitlines()

        for line in file_content:
            try:
                k, v = line.strip().split(': ', 1)
                if k != 'beatmapid':
                    continue

                bmap_id = int(v)
                if bmap_id > 0:
                    self.original_md5_or_bmapid = bmap_id
                    return bmap_id # type: ignore
            except:
                continue

    async def modified_txt_search(self) -> Optional[FUNORANGE_MAP]:
        if not glob.modified_txt.exists():
            return

        modified_maps = tuple(glob.modified_txt.read_text().splitlines())

        for modified_map_str in modified_maps:
            split = modified_map_str.split('.mp3 | ', 1)
            if len(split) < 2:
                continue

            audio, file_path = split

            file_path = Path(file_path)

            if glob.using_wsl:
                funorange_filename_from_txt = file_path.name.split("\\")[-1]
            else:
                funorange_filename_from_txt = file_path.parts[-1]

            if self.filename == funorange_filename_from_txt:
                self.funorange_map_path = file_path

                if glob.using_wsl:
                    self.funorange_map_path = await utils.str_to_wslpath(
                        path = str(file_path)
                    )

                break

        return self.funorange_map_path