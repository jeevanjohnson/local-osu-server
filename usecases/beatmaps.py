from repositories.sessions import SessionRepository
from constants import BEATMAPS_FILE, SESSIONS_FILE, PROFILES_FILE
from repositories.beatmaps import BeatmapsRepository
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
    CurrentBeatmapSet as BeatmapSet,
)
from usecases.providers import get_ossapi_async
import hashlib
from pathlib import Path
from repositories.profiles import ProfilesRepository
from osuProtocol.client_web import osuMapStatus
import asyncio
import aiohttp
import httpx
import time
from osu_file import OsuFile
from models.database.profiles import CurrentSettings
from datetime import datetime
from osuProtocol.server_packets import osuGameMode
import re
import ossapi
import functools


FILENAME_REGEX = re.compile(
    r"(?P<artist>.*) - (?P<song_name>.*) ((?P<mapper>.*) \[)(?P<diff_name>.*)\]\.osu"
)
DIFFICULTY_ADJUSTED_REGEX = re.compile(
    r"(?P<rate>[0-9]{1,2}(?:\.[0-9]{1,2})?x) \((?P<bpm>[0-9]+bpm)\)"
)
ATTRIBUTE_EDIT_REGEX = re.compile(
    r'(.*) (HP|CS|AR|OD)([0-9]{1,2}(?:\.[0-9]{1,2})?)'
)

class BeatmapResolver:
    def __init__(
            self,
            songs_folder: Path,
            beatmaps_repo: BeatmapsRepository,
            current_settings: CurrentSettings,
            http_session: aiohttp.ClientSession | None = None,
        ) -> None:
        self.beatmaps_repo = beatmaps_repo
        self.current_settings = current_settings
        self.songs_folder = songs_folder
        self._http_session = http_session
        self._owns_http_session = False

    def _get_http_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
            self._owns_http_session = True

        return self._http_session

    async def close(self) -> None:
        if self._owns_http_session and self._http_session is not None and not self._http_session.closed:
            await self._http_session.close()
    
    @staticmethod
    def build_from_bmap_api(
        api_beatmap: ossapi.Beatmap,
        status: osuMapStatus,
        osu_file_content: bytes
    ) -> Beatmap:
        beatmap_set = api_beatmap.beatmapset()
        
        assert beatmap_set is not None, "BeatmapSet not found for Beatmap with id {}".format(api_beatmap.id)
        assert api_beatmap.checksum is not None, "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        assert api_beatmap.max_combo is not None, "Max combo not found for Beatmap with id {}".format(api_beatmap.id)

        return Beatmap(
            time_inserted=datetime.now(),
            id=api_beatmap.id,
            set_id=api_beatmap.beatmapset_id,
            md5=api_beatmap.checksum,
            artist=beatmap_set.artist,
            title=beatmap_set.title,
            difficulty_name=api_beatmap.version,
            max_combo=api_beatmap.max_combo,
            status=status,
            mode=osuGameMode.from_api_v2(api_beatmap.mode),
            difficulty_adjusted=False,
            osu_file_content=osu_file_content
        )

    def is_difficulty_adjusted_from_filename(self, file_name: str) -> bool:
        # check modified_mp3_list.txt format first
        
        modified_mp3_list_txt = self.songs_folder / "modified_mp3_list.txt"
        if not modified_mp3_list_txt.exists():
            return False

        for line in modified_mp3_list_txt.read_text().splitlines():
            audio, map_path = line.split('.mp3 | ', maxsplit=1)
            map_path = Path(map_path)

            if map_path.parent / file_name == map_path:
                return True

        return False

    @staticmethod
    @functools.cache
    def valid_difficulty_adjusted_beatmap_filename(file_name: str) -> bool:
        file_name_data = FILENAME_REGEX.search(file_name)
        if not file_name_data:
            return False

        difficulty_name = file_name_data["diff_name"]
        if not difficulty_name:
            return False

        has_rate_adjust = bool(DIFFICULTY_ADJUSTED_REGEX.search(difficulty_name))
        has_attribute_adjust = bool(ATTRIBUTE_EDIT_REGEX.search(difficulty_name))

        # Accept either type of adjustment: rate-only (e.g. 0.89x (240bpm))
        # or explicit stat edits (AR/CS/HP/OD).
        return has_rate_adjust or has_attribute_adjust

    async def get_file_content(self, beatmap_id: int) -> bytes | None:
        url = f'https://osu.ppy.sh/osu/{beatmap_id}'
        http_session = self._get_http_session()

        async with http_session.get(url) as response:
            if not response or response.status != 200:
                return

            content = await response.content.read()

            if not content:
                return
            
            return content

    def from_db(self, beatmap_md5: str | None = None, beatmap_id: int | None = None) -> Beatmap | None:
        if beatmap_md5 is not None:
            return self.beatmaps_repo.get_by_md5(beatmap_md5)
        
        if beatmap_id is not None:
            return self.beatmaps_repo.get_by_id(beatmap_id)
        
        return None
    
    async def from_api_md5(self, beatmap_md5: str) -> Beatmap | None:
        osuApiAsync = await get_ossapi_async()

        try:
            api_beatmap = await osuApiAsync.beatmap(
                checksum=beatmap_md5
            )
        except ValueError as e:
            print(f"Error fetching beatmap with md5 {beatmap_md5} from osu api: {e}")
            return None

        if api_beatmap is None:
            return None
        
        osu_file = await self.get_file_content(api_beatmap.id)
        if osu_file is None:
            return None
        
        beatmap_set = api_beatmap.beatmapset()

        assert beatmap_set is not None, "BeatmapSet not found for Beatmap with id {}".format(api_beatmap.id)
        assert api_beatmap.checksum is not None, "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        assert api_beatmap.max_combo is not None, "Max combo not found for Beatmap with id {}".format(api_beatmap.id)

        return self.build_from_bmap_api(
            api_beatmap=api_beatmap,
            status=osuMapStatus.from_api_v2(api_beatmap.status),
            osu_file_content=osu_file
        )

    async def from_api_id(self, beatmap_id: int) -> Beatmap | None:
        osuApiAsync = await get_ossapi_async()

        api_beatmap = await osuApiAsync.beatmap(
            beatmap_id=beatmap_id
        )

        if api_beatmap is None:
            return None
        
        osu_file = await self.get_file_content(api_beatmap.id)
        if osu_file is None:
            return None
        
        beatmap_set = api_beatmap.beatmapset()

        assert beatmap_set is not None, "BeatmapSet not found for Beatmap with id {}".format(api_beatmap.id)
        assert api_beatmap.checksum is not None, "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        assert api_beatmap.max_combo is not None, "Max combo not found for Beatmap with id {}".format(api_beatmap.id)

        return self.build_from_bmap_api(
            api_beatmap=api_beatmap,
            status=osuMapStatus.from_api_v2(api_beatmap.status),
            osu_file_content=osu_file
        )

    def get_osu_file_from_md5(self, beatmap_md5: str) -> tuple[Path, OsuFile] | None:
        for osu_file in self.songs_folder.glob("**/*.osu"):
            if hashlib.md5(osu_file.read_bytes()).hexdigest() == beatmap_md5:
                parsed_osu_file = OsuFile(str(osu_file.absolute())).parse_file()
                return osu_file, parsed_osu_file
        
        return None

    def get_osu_file_from_set_and_filename(
        self,
        beatmap_set_id: int,
        map_filename: str,
    ) -> tuple[Path, OsuFile] | None:
        # Fast path: resolve file directly from provided set id + filename.
        for set_folder in self.songs_folder.glob(f"{beatmap_set_id}*"):
            if not set_folder.is_dir():
                continue

            osu_file = set_folder / map_filename
            if not osu_file.exists():
                continue

            parsed_osu_file = OsuFile(str(osu_file.absolute())).parse_file()
            return osu_file, parsed_osu_file

        return None
    
    def get_id_from_md5_in_songs_folder(self, beatmap_md5: str) -> int | None:
        osu_file = self.get_osu_file_from_md5(beatmap_md5)
        if osu_file is None:
            return None

        osu_file_parsed = OsuFile(str(osu_file))
        return osu_file_parsed.beatmap_id
    
    def build_difficulty_adjusted_beatmap(
            self, 
            original_beatmap: Beatmap, 
            difficulty_adjusted_md5: str,
            osu_file_path: Path) -> Beatmap:
        return Beatmap(
            time_inserted=datetime.now(),
            id=original_beatmap.id,
            set_id=original_beatmap.set_id,
            md5=difficulty_adjusted_md5,
            artist=original_beatmap.artist,
            title=original_beatmap.title,
            difficulty_name=original_beatmap.difficulty_name,
            max_combo=original_beatmap.max_combo,
            status=original_beatmap.status,
            mode=original_beatmap.mode,
            difficulty_adjusted=True,
            osu_file_content=osu_file_path.read_bytes()
        )

    async def from_leaderboard_request(
        self,
        beatmap_md5: str,
        beatmap_set_id: int,
        map_filename: str
    ) -> Beatmap | None:
        # 1. Check DB for beatmap with md5
        # 2. If not found, fetch from API using md5
        # 3. If thats not found validate that its a difficulty adjusted beatmap
        # 4. if it is, get original beatmap id from songs folder using md5, then fetch original beatmap from API using id
        # 5. Build difficulty adjusted beatmap using original beatmap data and osu file from songs folder, then insert to DB and return
        # 6. if its not a difficulty adjusted beatmap, return None?
        
        # DB Check
        beatmap = self.from_db(beatmap_md5)
        if beatmap:
            return beatmap

        # API Check
        try:
            beatmap = await self.from_api_md5(beatmap_md5)
        except ValueError as e:
            if "osuMapStatus" in str(e):
                print(f"Irrelevant Status for fetching leaderboards beatmap with md5 {beatmap_md5}")
                return None

        if beatmap:
            self.beatmaps_repo.insert_beatmap(beatmap)
            return beatmap
        
        # Not found in DB or API, check if its a difficulty adjusted beatmap

        # Difficulty Adjusted Check
        if not self.current_settings.difficulty_adjusted_beatmaps.sync_rank_status_with_bancho:
            return None

        if not self.valid_difficulty_adjusted_beatmap_filename(map_filename):
            return None

        # Since the beatmap is difficulty adjusted, get og id
        result = self.get_osu_file_from_set_and_filename(
            beatmap_set_id=beatmap_set_id,
            map_filename=map_filename,
        )

        if result is not None:
            osu_file_path, osu_file = result
            # Safety check: if direct path does not match request md5, fallback to full md5 scan.
            if osu_file.md5 != beatmap_md5:
                result = self.get_osu_file_from_md5(beatmap_md5)

        if result is None:
            result = self.get_osu_file_from_md5(beatmap_md5)

        if result is None:
            return None

        # Prefer list verification when available, but don't block valid resolved maps.
        if not self.is_difficulty_adjusted_from_filename(map_filename):
            print(
                "Warning: difficulty-adjusted map not found in modified_mp3_list.txt "
                f"for filename '{map_filename}', continuing via resolved .osu file"
            )
        
        osu_file_path, osu_file = result

        original_beatmap = self.from_db(beatmap_id=osu_file.beatmap_id)
        if original_beatmap is None:
            original_beatmap = await self.from_api_id(beatmap_id=osu_file.beatmap_id)

        if original_beatmap is None:
            return None

        difficulty_adjusted_beatmap = self.build_difficulty_adjusted_beatmap(
            original_beatmap, 
            beatmap_md5,
            osu_file_path
        )
        self.beatmaps_repo.insert_beatmap(difficulty_adjusted_beatmap)
        return difficulty_adjusted_beatmap

async def from_leaderboard_request(
    beatmap_md5: str,
    beatmap_set_id: int,
    map_filename: str,
    songs_folder: Path,
    current_settings: CurrentSettings
) -> Beatmap | None:
    resolver = BeatmapResolver(
        songs_folder=songs_folder,
        beatmaps_repo=BeatmapsRepository(BEATMAPS_FILE),
        current_settings=current_settings
    )

    try:
        return await resolver.from_leaderboard_request(
            beatmap_md5=beatmap_md5,
            beatmap_set_id=beatmap_set_id,
            map_filename=map_filename
        )
    finally:
        await resolver.close()