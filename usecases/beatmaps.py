import asyncio
import functools
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import ossapi

from adapters.app_logger import app_logger
from constants import BEATMAPS_FILE, OSU_FILES_FILE
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
    CurrentBeatmapSet as BeatmapSet,
)
from models.database.osu_files import CurrentOsuFileEntry as OsuFileEntry
from models.database.profiles import CurrentSettings
from models.domain.errors import BeatmapNotFoundError
from models.domain.gameplay import osuGameMode
from osuProtocol.client_web import osuMapStatus
from repositories.beatmaps import BeatmapsRepository
from repositories.osu_files import OsuFilesRepository
from usecases.providers import get_ossapi_async
from adapters import OsuFile

FILENAME_REGEX = re.compile(
    r"(?P<artist>.*) - (?P<song_name>.*) ((?P<mapper>.*) \[)(?P<diff_name>.*)\]\.osu"
)
DIFFICULTY_ADJUSTED_REGEX = re.compile(
    r"(?P<rate>[0-9]{1,2}(?:\.[0-9]{1,2})?x) \((?P<bpm>[0-9]+bpm)\)"
)
ATTRIBUTE_EDIT_REGEX = re.compile(r"(.*) (HP|CS|AR|OD)([0-9]{1,2}(?:\.[0-9]{1,2})?)")

_BEATMAP_HOT_CACHE_MAX_SIZE = 512
_beatmap_hot_cache_by_md5: dict[str, Beatmap] = {}
_OSU_FILE_PATH_CACHE_MAX_SIZE = 4096
_osu_file_path_by_md5: dict[str, Path] = {}
_osu_file_path_by_set_and_filename: dict[tuple[int, str], Path] = {}
_NON_EXPIRING_STATUSES = {
    osuMapStatus.RANKED,
    osuMapStatus.APPROVED,
    osuMapStatus.LOVED,
}
_UNSTABLE_MAP_TTL = timedelta(minutes=30)
_BEATMAP_DEBUG = False
_audio_background_tasks: set[asyncio.Task[None]] = set()
_audio_warmup_inflight_md5: set[str] = set()
_osu_file_persist_background_tasks: set[asyncio.Task[None]] = set()
_osu_file_persist_inflight_keys: set[tuple[str, bool]] = set()
_osu_file_persist_state: dict[str, bool] = {}
_set_persist_background_tasks: set[asyncio.Task[None]] = set()
_set_persist_inflight_set_ids: set[int] = set()


def _debug(msg: str) -> None:
    # Keep a separate toggle for branch-level resolver traces; @log already covers
    # function entry/exit and errors, while this is for deep path diagnostics.
    if _BEATMAP_DEBUG:
        app_logger.warning(f"[beatmap-resolver] {msg}")


def _get_cached_beatmap_by_md5(beatmap_md5: str) -> Beatmap | None:
    return _beatmap_hot_cache_by_md5.get(beatmap_md5)


def _remove_cached_beatmap_by_md5(beatmap_md5: str) -> None:
    _beatmap_hot_cache_by_md5.pop(beatmap_md5, None)


def _cache_beatmap(beatmap: Beatmap) -> None:
    # Keep a small FIFO cache to avoid repeated DB/API work for hot maps.
    if beatmap.md5 in _beatmap_hot_cache_by_md5:
        _beatmap_hot_cache_by_md5[beatmap.md5] = beatmap
        return

    if len(_beatmap_hot_cache_by_md5) >= _BEATMAP_HOT_CACHE_MAX_SIZE:
        oldest_key = next(iter(_beatmap_hot_cache_by_md5))
        del _beatmap_hot_cache_by_md5[oldest_key]

    _beatmap_hot_cache_by_md5[beatmap.md5] = beatmap


def _cache_osu_file_path_by_md5(md5: str, osu_file_path: Path) -> None:
    if md5 in _osu_file_path_by_md5:
        _osu_file_path_by_md5[md5] = osu_file_path
        return

    if len(_osu_file_path_by_md5) >= _OSU_FILE_PATH_CACHE_MAX_SIZE:
        oldest_key = next(iter(_osu_file_path_by_md5))
        del _osu_file_path_by_md5[oldest_key]

    _osu_file_path_by_md5[md5] = osu_file_path


def _cache_osu_file_path_by_set_and_filename(
    beatmap_set_id: int,
    map_filename: str,
    osu_file_path: Path,
) -> None:
    cache_key = (beatmap_set_id, map_filename)
    if cache_key in _osu_file_path_by_set_and_filename:
        _osu_file_path_by_set_and_filename[cache_key] = osu_file_path
        return

    if len(_osu_file_path_by_set_and_filename) >= _OSU_FILE_PATH_CACHE_MAX_SIZE:
        oldest_key = next(iter(_osu_file_path_by_set_and_filename))
        del _osu_file_path_by_set_and_filename[oldest_key]

    _osu_file_path_by_set_and_filename[cache_key] = osu_file_path


class BeatmapResolver:
    @app_logger.log(msg="beatmap resolver init")
    def __init__(
        self,
        songs_folder: Path,
        beatmaps_repo: BeatmapsRepository,
        osu_files_repo: OsuFilesRepository,
        current_settings: CurrentSettings,
        http_session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.beatmaps_repo = beatmaps_repo
        self.osu_files_repo = osu_files_repo
        self.current_settings = current_settings
        self.songs_folder = songs_folder
        self._http_session = http_session
        self._owns_http_session = False

    @app_logger.log(msg="beatmap resolver get http session")
    def _get_http_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
            self._owns_http_session = True

        return self._http_session

    @app_logger.log(msg="beatmap resolver close")
    async def close(self) -> None:
        if (
            self._owns_http_session
            and self._http_session is not None
            and not self._http_session.closed
        ):
            await self._http_session.close()

    @staticmethod
    @app_logger.log(msg="beatmap resolver build from api")
    def build_from_bmap_api(
        api_beatmap: ossapi.Beatmap,
        status: osuMapStatus,
        beatmap_set: ossapi.Beatmapset | ossapi.BeatmapsetCompact | None = None,
    ) -> Beatmap:
        if beatmap_set is None:
            beatmap_set = api_beatmap.beatmapset()

        assert beatmap_set is not None, (
            "BeatmapSet not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert api_beatmap.checksum is not None, (
            "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert api_beatmap.max_combo is not None, (
            "Max combo not found for Beatmap with id {}".format(api_beatmap.id)
        )

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
        )

    @app_logger.log(msg="beatmap resolver persist osu file")
    async def _persist_osu_file(self, beatmap_md5: str, osu_file: OsuFile) -> None:
        await self.osu_files_repo.upsert(OsuFileEntry(md5=beatmap_md5, file=osu_file))

    @staticmethod
    @app_logger.log(msg="beatmap resolver should skip osu file persist")
    def _should_skip_osu_file_persist(beatmap_md5: str, has_audio: bool) -> bool:
        persisted_has_audio = _osu_file_persist_state.get(beatmap_md5)
        if persisted_has_audio is None:
            return False

        # Once audio has been persisted, there is no higher-fidelity payload to store.
        if persisted_has_audio:
            return True

        # Skip repeated no-audio writes; allow upgrading no-audio -> has-audio.
        return not has_audio

    @app_logger.log(msg="beatmap resolver schedule osu file persist")
    def _schedule_persist_osu_file(self, beatmap_md5: str, osu_file: OsuFile) -> None:
        has_audio = osu_file.raw_audio_file is not None

        if self._should_skip_osu_file_persist(beatmap_md5, has_audio):
            return

        inflight_key = (beatmap_md5, has_audio)
        if inflight_key in _osu_file_persist_inflight_keys:
            return

        _osu_file_persist_inflight_keys.add(inflight_key)

        async def _persist() -> None:
            try:
                await self._persist_osu_file(beatmap_md5, osu_file)
                previous_has_audio = _osu_file_persist_state.get(beatmap_md5, False)
                _osu_file_persist_state[beatmap_md5] = previous_has_audio or has_audio
            finally:
                _osu_file_persist_inflight_keys.discard(inflight_key)

        task = asyncio.create_task(_persist())
        _osu_file_persist_background_tasks.add(task)
        task.add_done_callback(_osu_file_persist_background_tasks.discard)

    @staticmethod
    @app_logger.log(msg="beatmap resolver check stale unstable map")
    def _should_refresh_stale_unstable_map(beatmap: Beatmap) -> bool:
        if beatmap.status in _NON_EXPIRING_STATUSES:
            return False

        return datetime.now() - beatmap.time_inserted > _UNSTABLE_MAP_TTL

    @app_logger.log(msg="beatmap resolver store full set")
    async def _store_full_set_if_eligible(
        self,
        requested_api_beatmap: ossapi.Beatmap,
        requested_osu_file_content: OsuFile,
    ) -> None:
        beatmap_set = requested_api_beatmap.beatmapset()
        if beatmap_set is None or not beatmap_set.beatmaps:
            return

        set_maps: list[Beatmap] = []
        for api_set_map in beatmap_set.beatmaps:
            if api_set_map.checksum is None or api_set_map.max_combo is None:
                continue

            set_map_status = osuMapStatus.from_api_v2(api_set_map.status)

            # Only the requested beatmap has guaranteed .osu bytes on this path.
            set_map_osu_content = (
                requested_osu_file_content
                if api_set_map.id == requested_api_beatmap.id
                else None
            )

            parsed_set_map = self.build_from_bmap_api(
                api_beatmap=api_set_map,
                status=set_map_status,
                beatmap_set=beatmap_set,
            )
            set_maps.append(parsed_set_map)

            if set_map_osu_content is not None:
                self._schedule_persist_osu_file(parsed_set_map.md5, set_map_osu_content)
                self._schedule_audio_warmup(parsed_set_map.md5, set_map_osu_content)

        if not set_maps:
            return

        await self.beatmaps_repo.insert_beatmap_set(
            BeatmapSet(id=requested_api_beatmap.beatmapset_id, maps=set_maps)
        )

        for parsed_set_map in set_maps:
            _cache_beatmap(parsed_set_map)

    @app_logger.log(msg="beatmap resolver schedule set persist")
    def _schedule_store_full_set_if_eligible(
        self,
        requested_api_beatmap: ossapi.Beatmap,
        requested_osu_file_content: OsuFile,
    ) -> None:
        set_id = requested_api_beatmap.beatmapset_id
        if set_id in _set_persist_inflight_set_ids:
            return

        _set_persist_inflight_set_ids.add(set_id)

        async def _persist_set() -> None:
            try:
                await self._store_full_set_if_eligible(
                    requested_api_beatmap=requested_api_beatmap,
                    requested_osu_file_content=requested_osu_file_content,
                )
            finally:
                _set_persist_inflight_set_ids.discard(set_id)

        task = asyncio.create_task(_persist_set())
        _set_persist_background_tasks.add(task)
        task.add_done_callback(_set_persist_background_tasks.discard)

    @app_logger.log(msg="beatmap resolver check diff adjusted from filename")
    def is_difficulty_adjusted_from_filename(self, file_name: str) -> bool:
        # check modified_mp3_list.txt format first

        modified_mp3_list_txt = self.songs_folder / "modified_mp3_list.txt"
        if not modified_mp3_list_txt.exists():
            return False

        for line in modified_mp3_list_txt.read_text().splitlines():
            audio, map_path = line.split(".mp3 | ", maxsplit=1)
            map_path = Path(map_path)

            if map_path.parent / file_name == map_path:
                return True

        return False

    @staticmethod
    @app_logger.log(msg="beatmap resolver validate diff adjusted filename")
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

    @app_logger.log(msg="beatmap resolver get audio file in songs folder")
    def get_audio_file_in_songs_folder(self, beatmap_md5: str) -> Path | None:
        # Implementation for finding audio file in songs folder
        pass

    # async def get_file_content(self, beatmap_id: int) -> OsuFile | None:
    #     url = f"https://osu.ppy.sh/osu/{beatmap_id}"
    #     http_session = self._get_http_session()
    #     _debug(f"Downloading .osu content from api for beatmap_id={beatmap_id}")

    #     async with http_session.get(url) as response:
    #         if not response or response.status != 200:
    #             _debug(
    #                 f"Failed downloading .osu for beatmap_id={beatmap_id}, status={getattr(response, 'status', None)}"
    #             )
    #             return

    #         content = await response.content.read()

    #         if not content:
    #             _debug(f"Empty .osu content received for beatmap_id={beatmap_id}")
    #             return

    #         _debug(f"Downloaded .osu content for beatmap_id={beatmap_id}")
    #         return OsuFile.from_raw(content)

    @app_logger.log(msg="beatmap resolver from db")
    async def from_db(
        self, beatmap_md5: str | None = None, beatmap_id: int | None = None
    ) -> Beatmap | None:
        if beatmap_md5 is not None:
            try:
                return await self.beatmaps_repo.require_by_md5(beatmap_md5)
            except BeatmapNotFoundError:
                return None

        if beatmap_id is not None:
            try:
                return await self.beatmaps_repo.require_by_id(beatmap_id)
            except BeatmapNotFoundError:
                return None

        return None

    @app_logger.log(msg="beatmap resolver ensure audio loaded")
    def _ensure_audio_loaded(self, osu_file: OsuFile, beatmap_md5: str) -> None:
        if osu_file.raw_audio_file is not None:
            return

        audio = osu_file.get_audio_file()
        if audio is None:
            _debug(
                f"No audio file found for md5={beatmap_md5}; storing empty audio payload"
            )
        else:
            _debug(
                f"Loaded audio bytes for md5={beatmap_md5} (size={len(audio)} bytes)"
            )

    @app_logger.log(msg="beatmap resolver schedule audio warmup")
    def _schedule_audio_warmup(self, beatmap_md5: str, osu_file: OsuFile) -> None:
        if osu_file.raw_audio_file is not None:
            return

        if beatmap_md5 in _audio_warmup_inflight_md5:
            return

        _audio_warmup_inflight_md5.add(beatmap_md5)

        async def _load_and_persist_audio() -> None:
            try:
                await asyncio.to_thread(
                    self._ensure_audio_loaded,
                    osu_file,
                    beatmap_md5,
                )
                if osu_file.raw_audio_file is not None:
                    self._schedule_persist_osu_file(beatmap_md5, osu_file)
            finally:
                _audio_warmup_inflight_md5.discard(beatmap_md5)

        task = asyncio.create_task(_load_and_persist_audio())
        _audio_background_tasks.add(task)
        task.add_done_callback(_audio_background_tasks.discard)

    @app_logger.log(msg="beatmap resolver from api md5")
    async def from_api_md5(
        self, beatmap_md5: str, filename: str | None = None
    ) -> Beatmap | None:
        osuApiAsync = await get_ossapi_async()
        _debug(f"API md5 lookup start md5={beatmap_md5}")

        try:
            api_beatmap = await osuApiAsync.beatmap(checksum=beatmap_md5)
        except ValueError as e:
            app_logger.error(
                f"Error fetching beatmap with md5 {beatmap_md5} from osu api: {e}"
            )
            return None

        if api_beatmap is None:
            _debug(f"API md5 lookup miss md5={beatmap_md5}")
            return None

        _debug(
            "API md5 lookup hit "
            f"md5={beatmap_md5} beatmap_id={api_beatmap.id} set_id={api_beatmap.beatmapset_id} "
            f"status={api_beatmap.status}"
        )

        # get .osu file from songs folder
        if filename is None:
            osu_file = self.get_osu_file_from_md5_and_set_id(
                beatmap_md5, api_beatmap.beatmapset_id
            )
        else:
            osu_file = self.get_osu_file_from_set_and_filename(
                beatmap_set_id=api_beatmap.beatmapset_id,
                map_filename=filename,
            )

        if osu_file is None:
            # Attempt fallback
            app_logger.warning(
                f"Failed to find .osu file for beatmap with md5 {beatmap_md5} using set id hint, attempting full scan by md5"
            )
            _debug(
                f"Fast songs-folder lookup miss md5={beatmap_md5}, falling back to full md5 scan"
            )
            osu_file = self.get_osu_file_from_md5(beatmap_md5)

        if osu_file is None:
            _debug(f"Could not resolve local .osu file for md5={beatmap_md5}")
            return None

        self._schedule_persist_osu_file(beatmap_md5, osu_file)
        self._schedule_audio_warmup(beatmap_md5, osu_file)

        beatmap_set = api_beatmap.beatmapset()

        assert beatmap_set is not None, (
            "BeatmapSet not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert api_beatmap.checksum is not None, (
            "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert api_beatmap.max_combo is not None, (
            "Max combo not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert osu_file.raw_file is not None, (
            "Raw file content not found for Beatmap with id {}".format(api_beatmap.id)
        )

        self._schedule_store_full_set_if_eligible(
            requested_api_beatmap=api_beatmap,
            requested_osu_file_content=osu_file,
        )

        _debug(
            f"Built beatmap from API md5 md5={beatmap_md5} beatmap_id={api_beatmap.id} status={api_beatmap.status}"
        )

        return self.build_from_bmap_api(
            api_beatmap=api_beatmap,
            status=osuMapStatus.from_api_v2(api_beatmap.status),
            beatmap_set=beatmap_set,
        )

    @app_logger.log(msg="beatmap resolver from api id")
    async def from_api_id(
        self, beatmap_id: int, filename: str | None = None
    ) -> Beatmap | None:
        osuApiAsync = await get_ossapi_async()
        _debug(f"API id lookup start beatmap_id={beatmap_id}")

        api_beatmap = await osuApiAsync.beatmap(beatmap_id=beatmap_id)

        if api_beatmap is None:
            _debug(f"API id lookup miss beatmap_id={beatmap_id}")
            return None

        _debug(
            f"API id lookup hit beatmap_id={beatmap_id} md5={api_beatmap.checksum} status={api_beatmap.status}"
        )

        # osu_file = await self.get_file_content(api_beatmap.id)
        if filename is None:
            assert api_beatmap.checksum is not None, (
                "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
            )
            osu_file = self.get_osu_file_from_md5_and_set_id(
                api_beatmap.checksum, api_beatmap.beatmapset_id
            )
        else:
            osu_file = self.get_osu_file_from_set_and_filename(
                beatmap_set_id=api_beatmap.beatmapset_id,
                map_filename=filename,
            )

        if osu_file is None:
            return None

        assert api_beatmap.checksum is not None, (
            "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        )
        self._schedule_persist_osu_file(api_beatmap.checksum, osu_file)
        self._schedule_audio_warmup(api_beatmap.checksum, osu_file)

        beatmap_set = api_beatmap.beatmapset()

        assert beatmap_set is not None, (
            "BeatmapSet not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert api_beatmap.checksum is not None, (
            "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert api_beatmap.max_combo is not None, (
            "Max combo not found for Beatmap with id {}".format(api_beatmap.id)
        )
        assert osu_file.raw_file is not None, (
            "Raw file content not found for Beatmap with id {}".format(api_beatmap.id)
        )

        self._schedule_store_full_set_if_eligible(
            requested_api_beatmap=api_beatmap,
            requested_osu_file_content=osu_file,
        )

        return self.build_from_bmap_api(
            api_beatmap=api_beatmap,
            status=osuMapStatus.from_api_v2(api_beatmap.status),
            beatmap_set=beatmap_set,
        )

    @app_logger.log(msg="beatmap resolver get osu file by md5 and set")
    def get_osu_file_from_md5_and_set_id(
        self, beatmap_md5: str, beatmap_set_id: int
    ) -> OsuFile | None:
        cached_path = _osu_file_path_by_md5.get(beatmap_md5)
        if cached_path is not None:
            if cached_path.exists():
                return OsuFile.from_path(
                    str(cached_path.absolute()),
                    load_audio_file=False,
                )

            _osu_file_path_by_md5.pop(beatmap_md5, None)

        _debug(
            f"Songs-folder fast scan start md5={beatmap_md5} set_id={beatmap_set_id}"
        )
        for set_folder in self.songs_folder.glob(f"{beatmap_set_id}*"):
            if not set_folder.is_dir():
                continue

            for osu_file in set_folder.glob("*.osu"):
                if hashlib.md5(osu_file.read_bytes()).hexdigest() == beatmap_md5:
                    _cache_osu_file_path_by_md5(beatmap_md5, osu_file)
                    _cache_osu_file_path_by_set_and_filename(
                        beatmap_set_id=beatmap_set_id,
                        map_filename=osu_file.name,
                        osu_file_path=osu_file,
                    )
                    _debug(
                        f"Songs-folder fast scan hit md5={beatmap_md5} path={osu_file}"
                    )
                    return OsuFile.from_path(
                        str(osu_file.absolute()),
                        load_audio_file=False,
                    )

        _debug(f"Songs-folder fast scan miss md5={beatmap_md5} set_id={beatmap_set_id}")
        return None

    @app_logger.log(msg="beatmap resolver get osu file by md5")
    def get_osu_file_from_md5(self, beatmap_md5: str) -> OsuFile | None:
        cached_path = _osu_file_path_by_md5.get(beatmap_md5)
        if cached_path is not None:
            if cached_path.exists():
                return OsuFile.from_path(
                    str(cached_path.absolute()),
                    load_audio_file=False,
                )

            _osu_file_path_by_md5.pop(beatmap_md5, None)

        _debug(f"Songs-folder full scan start md5={beatmap_md5}")
        for osu_file in self.songs_folder.glob("**/*.osu"):
            if hashlib.md5(osu_file.read_bytes()).hexdigest() == beatmap_md5:
                _cache_osu_file_path_by_md5(beatmap_md5, osu_file)
                _debug(f"Songs-folder full scan hit md5={beatmap_md5} path={osu_file}")
                return OsuFile.from_path(
                    str(osu_file.absolute()),
                    load_audio_file=False,
                )

        _debug(f"Songs-folder full scan miss md5={beatmap_md5}")
        return None

    @app_logger.log(msg="beatmap resolver get osu file by set and filename")
    def get_osu_file_from_set_and_filename(
        self,
        beatmap_set_id: int,
        map_filename: str,
    ) -> OsuFile | None:
        cache_key = (beatmap_set_id, map_filename)
        cached_path = _osu_file_path_by_set_and_filename.get(cache_key)
        if cached_path is not None:
            if cached_path.exists():
                parsed_osu_file = OsuFile.from_path(
                    str(cached_path.absolute()),
                    load_audio_file=False,
                )
                _cache_osu_file_path_by_md5(parsed_osu_file.md5, cached_path)
                return parsed_osu_file

            _osu_file_path_by_set_and_filename.pop(cache_key, None)

        # Fast path: resolve file directly from provided set id + filename.
        for set_folder in self.songs_folder.glob(f"{beatmap_set_id}*"):
            if not set_folder.is_dir():
                continue

            osu_file = set_folder / map_filename
            if not osu_file.exists():
                continue

            parsed_osu_file = OsuFile.from_path(
                str(osu_file.absolute()),
                load_audio_file=False,
            )
            _cache_osu_file_path_by_set_and_filename(
                beatmap_set_id=beatmap_set_id,
                map_filename=map_filename,
                osu_file_path=osu_file,
            )
            _cache_osu_file_path_by_md5(parsed_osu_file.md5, osu_file)
            return parsed_osu_file

        return None

    @app_logger.log(msg="beatmap resolver get id from md5 in songs")
    def get_id_from_md5_in_songs_folder(self, beatmap_md5: str) -> int | None:
        osu_file = self.get_osu_file_from_md5(beatmap_md5)
        if osu_file is None:
            return None

        return osu_file.beatmap_id

    @app_logger.log(msg="beatmap resolver build difficulty adjusted beatmap")
    def build_difficulty_adjusted_beatmap(
        self, original_beatmap: Beatmap, difficulty_adjusted_md5: str
    ) -> Beatmap:
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
        )

    @app_logger.log(msg="beatmap resolver from leaderboard request")
    async def from_leaderboard_request(
        self, beatmap_md5: str, beatmap_set_id: int, map_filename: str
    ) -> Beatmap | None:
        _debug(
            "Leaderboard resolve start "
            f"md5={beatmap_md5} set_id={beatmap_set_id} filename={map_filename}"
        )
        # 1. Check DB for beatmap with md5
        # 2. If not found, fetch from API using md5
        # 3. If thats not found validate that its a difficulty adjusted beatmap
        # 4. if it is, get original beatmap id from songs folder using md5, then fetch original beatmap from API using id
        # 5. Build difficulty adjusted beatmap using original beatmap data and osu file from songs folder, then insert to DB and return
        # 6. if its not a difficulty adjusted beatmap, return None?

        # Hot cache check
        beatmap = _get_cached_beatmap_by_md5(beatmap_md5)
        if beatmap:
            _debug(
                f"Hot cache hit md5={beatmap_md5} status={beatmap.status.name} inserted={beatmap.time_inserted.isoformat()}"
            )
            if self._should_refresh_stale_unstable_map(beatmap):
                _debug(f"Hot cache stale unstable map md5={beatmap_md5}, evicting")
                _remove_cached_beatmap_by_md5(beatmap_md5)
            else:
                _debug(f"Returning beatmap from hot cache md5={beatmap_md5}")
                return beatmap
        else:
            _debug(f"Hot cache miss md5={beatmap_md5}")

        # DB Check
        beatmap = await self.from_db(beatmap_md5)
        if beatmap:
            _debug(
                f"DB hit md5={beatmap_md5} status={beatmap.status.name} inserted={beatmap.time_inserted.isoformat()}"
            )
            if self._should_refresh_stale_unstable_map(beatmap):
                _debug(
                    f"DB stale unstable map md5={beatmap_md5}, deleting and refreshing"
                )
                await self.beatmaps_repo.delete_beatmap(beatmap)
                await self.osu_files_repo.delete_by_md5(beatmap.md5)
                _remove_cached_beatmap_by_md5(beatmap_md5)
            else:
                _debug(f"Returning beatmap from DB md5={beatmap_md5}")
                _cache_beatmap(beatmap)
                return beatmap
        else:
            _debug(f"DB miss md5={beatmap_md5}")

        # API Check
        beatmap = await self.from_api_md5(beatmap_md5, filename=map_filename)

        if beatmap:
            await self.beatmaps_repo.insert_beatmap(beatmap)
            _cache_beatmap(beatmap)
            _debug(
                f"Returning beatmap from API md5={beatmap_md5} status={beatmap.status.name} and cached in DB/hot-cache"
            )
            return beatmap

        _debug(
            f"API md5 path failed md5={beatmap_md5}, trying difficulty-adjusted resolution"
        )

        # Not found in DB or API, check if its a difficulty adjusted beatmap

        # Difficulty Adjusted Check
        if not self.current_settings.difficulty_adjusted_beatmaps.sync_rank_status_with_bancho:
            _debug("Difficulty-adjusted sync disabled, aborting resolution")
            return None

        if not self.valid_difficulty_adjusted_beatmap_filename(map_filename):
            _debug(
                f"Filename did not match difficulty-adjusted pattern filename={map_filename}"
            )
            return None

        # Since the beatmap is difficulty adjusted, get og id
        osu_file = self.get_osu_file_from_set_and_filename(
            beatmap_set_id=beatmap_set_id,
            map_filename=map_filename,
        )

        if osu_file is not None:
            # Safety check: if direct path does not match request md5, fallback to full md5 scan.
            if osu_file.md5 != beatmap_md5:
                osu_file = self.get_osu_file_from_md5(beatmap_md5)

        if osu_file is None:
            osu_file = self.get_osu_file_from_md5(beatmap_md5)

        if osu_file is None:
            _debug("Difficulty-adjusted path could not resolve .osu file")
            return None

        # Prefer list verification when available, but don't block valid resolved maps.
        if not self.is_difficulty_adjusted_from_filename(map_filename):
            app_logger.warning(
                "Warning: difficulty-adjusted map not found in modified_mp3_list.txt "
                f"for filename '{map_filename}', continuing via resolved .osu file"
            )

        original_beatmap = await self.from_db(beatmap_id=osu_file.beatmap_id)
        if original_beatmap is None:
            original_beatmap = await self.from_api_id(beatmap_id=osu_file.beatmap_id)

        if original_beatmap is None:
            _debug(
                f"Original beatmap not found for difficulty-adjusted map md5={beatmap_md5}, source beatmap_id={osu_file.beatmap_id}"
            )
            return None

        difficulty_adjusted_beatmap = self.build_difficulty_adjusted_beatmap(
            original_beatmap, beatmap_md5
        )
        self._schedule_persist_osu_file(beatmap_md5, osu_file)
        self._schedule_audio_warmup(beatmap_md5, osu_file)
        await self.beatmaps_repo.insert_beatmap(difficulty_adjusted_beatmap)
        _cache_beatmap(difficulty_adjusted_beatmap)
        _debug(
            f"Returning difficulty-adjusted beatmap md5={beatmap_md5} based_on_beatmap_id={original_beatmap.id}"
        )
        return difficulty_adjusted_beatmap

    @app_logger.log(msg="beatmap resolver from score submission request")
    async def from_score_submission_request(self, beatmap_md5: str) -> Beatmap | None:
        _debug(f"Score submission resolve start md5={beatmap_md5}")
        # Simpler path for score submissions since we don't have filename or set id hints to resolve from.
        # Just check DB and then API by md5.
        # TODO: Maybe attempt diff adjust via scanning songs folder?
        beatmap = await self.from_db(beatmap_md5)
        if beatmap:
            _debug(
                f"Score submission DB hit md5={beatmap_md5} status={beatmap.status.name}"
            )
            return beatmap

        _debug(f"Score submission DB miss md5={beatmap_md5}, trying API")
        beatmap = await self.from_api_md5(beatmap_md5)
        if beatmap:
            await self.beatmaps_repo.insert_beatmap(beatmap)
            _debug(
                f"Score submission API hit md5={beatmap_md5} status={beatmap.status.name}"
            )
            return beatmap

        _debug(f"Score submission resolve failed md5={beatmap_md5}")
        return None


@app_logger.log(msg="usecase beatmaps from leaderboard request")
async def from_leaderboard_request(
    beatmap_md5: str,
    beatmap_set_id: int,
    map_filename: str,
    songs_folder: Path,
    current_settings: CurrentSettings,
) -> Beatmap | None:
    resolver = BeatmapResolver(
        songs_folder=songs_folder,
        beatmaps_repo=BeatmapsRepository(BEATMAPS_FILE),
        osu_files_repo=OsuFilesRepository(OSU_FILES_FILE),
        current_settings=current_settings,
    )

    try:
        return await resolver.from_leaderboard_request(
            beatmap_md5=beatmap_md5,
            beatmap_set_id=beatmap_set_id,
            map_filename=map_filename,
        )
    finally:
        await resolver.close()


@app_logger.log(msg="usecase beatmaps from score submission request")
async def from_score_submission_request(
    beatmap_md5: str,
    songs_folder: Path,
    current_settings: CurrentSettings,
) -> Beatmap | None:
    resolver = BeatmapResolver(
        songs_folder=songs_folder,
        beatmaps_repo=BeatmapsRepository(BEATMAPS_FILE),
        osu_files_repo=OsuFilesRepository(OSU_FILES_FILE),
        current_settings=current_settings,
    )

    try:
        return await resolver.from_score_submission_request(beatmap_md5=beatmap_md5)
    finally:
        await resolver.close()
