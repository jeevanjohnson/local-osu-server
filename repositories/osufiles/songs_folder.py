import asyncio
import json
from pathlib import Path
from typing import Any

from usecases.adapters.osu_file import OsuFile
from usecases.domain.cache_control import cache_beatmaps

try:
    from constants.paths import CACHE_SONGS_FOLDER
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from constants.paths import CACHE_SONGS_FOLDER


class OsuFileRepository:
    """
    Singleton repository for accessing songs folder data.
    Loads JSON cache once, keeps it in memory, refreshes only if file is modified.
    """
    _instance: "OsuFileRepository | None" = None
    _lock: asyncio.Lock | None = None
    _data: dict[str, Any] | None = None
    _last_mtime: float = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
            cls._instance._data = None
            cls._instance._last_mtime = 0
        return cls._instance

    async def _ensure_loaded(self) -> None:
        """
        Load JSON cache file once, refresh only if file was modified.
        Uses mtime to detect changes efficiently.
        """
        if not CACHE_SONGS_FOLDER.exists():
            print(f"Cache file not found: {CACHE_SONGS_FOLDER}")
            return

        current_mtime = CACHE_SONGS_FOLDER.stat().st_mtime

        # Only reload if file changed or data not loaded yet
        if current_mtime > self._last_mtime or self._data is None:
            try:
                self._data = json.loads(CACHE_SONGS_FOLDER.read_text())
                self._last_mtime = current_mtime
                print(f"Loaded songs folder cache (mtime: {current_mtime})")
            except json.JSONDecodeError as e:
                print(f"Failed to parse cache JSON: {e}")
                self._data = None

    def _get_path_by_md5(self, md5: str) -> str | None:
        """Get file path from MD5 hash (synchronous lookup in memory)."""
        if self._data is None or "md5_to_path" not in self._data:
            return None
        return self._data["md5_to_path"].get(md5)

    def _get_paths_by_beatmap_id(self, beatmap_id: int) -> list[str] | None:
        """Get file paths from beatmap ID (synchronous lookup in memory)."""
        if self._data is None or "beatmap_id_to_path" not in self._data:
            return None
        return self._data["beatmap_id_to_path"].get(str(beatmap_id))

    def _get_path_by_filename(self, filename: str) -> str | None:
        """Get file path from filename (synchronous lookup in memory)."""
        if self._data is None or "filename_to_path" not in self._data:
            return None
        return self._data["filename_to_path"].get(filename)

    def _get_md5_by_path(self, path: str) -> str | None:
        """Get MD5 hash from file path (synchronous lookup in memory)."""
        if self._data is None or "path_to_md5" not in self._data:
            return None
        return self._data["path_to_md5"].get(path)


    @cache_beatmaps
    async def from_path_to_md5(self, path: Path) -> str | None:
        """Get MD5 hash from file path."""
        assert self._lock is not None
        async with self._lock:
            await self._ensure_loaded()
            return self._get_md5_by_path(str(path))

    @cache_beatmaps
    async def from_beatmap_id(
        self, beatmap_id: int, excluded_md5s: set[str] | None = None
    ) -> list[OsuFile] | None:
        """Get OsuFile objects from beatmap ID."""
        assert self._lock is not None
        async with self._lock:
            await self._ensure_loaded()
            osu_file_paths = self._get_paths_by_beatmap_id(beatmap_id)
        
        if osu_file_paths is None:
            return None

        result = []

        for path in (Path(p) for p in osu_file_paths):
            if excluded_md5s is not None:
                md5 = await self.from_path_to_md5(path)
                if md5 in excluded_md5s:
                    continue

            result.append(OsuFile.from_path(path))

        return result

    @cache_beatmaps
    async def from_md5(self, md5: str) -> OsuFile | None:
        """Get OsuFile object from MD5 hash."""
        assert self._lock is not None
        async with self._lock:
            await self._ensure_loaded()
            osu_file_path = self._get_path_by_md5(md5)
        
        if osu_file_path is None or osu_file_path == "":
            return None

        path = Path(osu_file_path).absolute()

        return OsuFile.from_path(path)

    @cache_beatmaps
    async def path_from_md5(self, md5: str) -> Path | None:
        """Get the file path for a beatmap by its MD5 hash."""
        assert self._lock is not None
        async with self._lock:
            await self._ensure_loaded()
            osu_file_path = self._get_path_by_md5(md5)
        
        if osu_file_path is None or osu_file_path == "":
            return None

        return Path(osu_file_path).absolute()

    @cache_beatmaps
    async def from_filename(self, filename: str) -> OsuFile | None:
        """Get OsuFile object from filename."""
        assert self._lock is not None
        async with self._lock:
            await self._ensure_loaded()
            osu_file_path = self._get_path_by_filename(filename)
        
        if osu_file_path is None or osu_file_path == "":
            return None

        path = Path(osu_file_path).absolute()

        return OsuFile.from_path(path)
