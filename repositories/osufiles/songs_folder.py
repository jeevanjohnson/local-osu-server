import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from usecases.adapters.osu_file import OsuFile
from processes.songs_folder import Commands


class OsuFileRepository:
    _instance: "OsuFileRepository | None" = None
    _process: "asyncio.subprocess.Process | None" = None
    _lock: asyncio.Lock | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def _ensure_subprocess(self) -> "asyncio.subprocess.Process":
        """Ensure subprocess is running, restarting if needed."""
        if self._process is None or self._process.returncode is not None:
            # Subprocess dead or not started; spawn new one
            self._process = await asyncio.create_subprocess_exec(
                sys.executable,
                "./processes/songs_folder.py",
                "--interactive",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for "ready" confirmation with timeout
            try:
                assert self._process.stderr is not None
                line = await asyncio.wait_for(
                    self._process.stderr.readline(), timeout=5.0
                )
                response = line.decode().strip()
                if "ready" not in response.lower():
                    print(f"Subprocess startup message: {response}")
            except asyncio.TimeoutError:
                print("Subprocess failed to start")
                self._process = None
                raise

        return self._process

    async def run_command(self, command_name: Commands, parameter: str) -> Any:
        assert self._lock is not None
        async with self._lock:
            process = await self._ensure_subprocess()

            # Send command via stdin
            cmd_line = f"{command_name.value}|{parameter}\n"
            assert process.stdin is not None
            process.stdin.write(cmd_line.encode())
            await process.stdin.drain()

            # Read response from stderr
            assert process.stderr is not None
            response_line = await process.stderr.readline()
            decoded = response_line.decode().strip()

            if not decoded:
                print(f"No response from subprocess for command {command_name}")
                return None

            try:
                response_data = json.loads(decoded)

                if "error" in response_data:
                    print(f"Command error: {response_data['error']}")
                    return None

                result = response_data.get("result")
                print(
                    f"Command {command_name} with parameter {parameter} returned output: {result}"
                )
                return result
            except json.JSONDecodeError as e:
                print(f"Failed to decode response: {decoded} - {e}")
                return None

    # @cached_for_10_minutes
    async def from_path_to_md5(self, path: Path) -> str | None:
        md5 = await self.run_command(Commands.GET_MD5_BY_PATH, str(path))
        if md5 is None:
            return None

        return md5

    # @cached_for_10_minutes
    async def from_beatmap_id(
        self, beatmap_id: int, excluded_md5s: set[str] | None = None
    ) -> list[OsuFile] | None:
        osu_file_paths: list[str] | None = await self.run_command(
            Commands.GET_PATH_BY_BEATMAP_ID, str(beatmap_id)
        )
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

    # @cached_for_10_minutes
    async def from_md5(self, md5: str) -> OsuFile | None:
        osu_file_path = await self.run_command(Commands.GET_PATH_BY_MD5, md5)
        if osu_file_path is None or osu_file_path == "":
            return None

        path = Path(osu_file_path).absolute()

        return OsuFile.from_path(path)

    async def path_from_md5(self, md5: str) -> Path | None:
        """Get the file path for a beatmap by its MD5 hash."""
        osu_file_path = await self.run_command(Commands.GET_PATH_BY_MD5, md5)
        if osu_file_path is None or osu_file_path == "":
            return None

        return Path(osu_file_path).absolute()

    # @cached_for_10_minutes
    async def from_filename(self, filename: str) -> OsuFile | None:
        osu_file_path = await self.run_command(Commands.GET_PATH_BY_FILENAME, filename)
        if osu_file_path is None or osu_file_path == "":
            return None

        path = Path(osu_file_path).absolute()

        return OsuFile.from_path(path)
