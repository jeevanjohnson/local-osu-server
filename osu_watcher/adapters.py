from jays_tools.architecture import Adapter
import psutil
from pathlib import Path
import os
from hachiko.hachiko import AIOWatchdog as BaseAIOWatchdog, AIOEventHandler
from watchdog.observers import Observer

class AIOWatchdog(BaseAIOWatchdog, Adapter):
    def __init__(
        self, 
        path=".", 
        recursive=True, 
        event_handler=None, 
        observer=None
    ):
        if observer is None:
            self._observer = Observer()
        else:
            self._observer = observer

        evh = event_handler or AIOEventHandler()

        self._observer.schedule(
            evh, # type: ignore
            path, 
            recursive=recursive
        )

    def join(self) -> None:
        self._observer.join()

class OsuClientAdapter(Adapter):
    def get_osu_process(self) -> psutil.Process | None:
        try:
            processes = [
                process for process in psutil.process_iter() if process.name() == "osu!.exe"
            ]
            if not processes:
                return None

            return processes[0]
        except psutil.NoSuchProcess:
            return None
    
    def get_osu_client_path(self) -> Path:
        osu_process = self.get_osu_process()

        if osu_process is None:
            raise Exception("osu!.exe wasn't found")

        path_str = osu_process.exe()

        if not path_str:
            raise Exception("osu!.exe process was found but path doesn't exists")

        return Path(path_str)

    def get_osu_directory(self) -> Path:
        osu_client_path = self.get_osu_client_path()
        return osu_client_path.parent

class OsuDirectoryAdapter(Adapter):
    def get_config_file(self, osu_directory: Path) -> Path | None:
        config_path: Path | None = None
        for config_file in osu_directory.glob("osu!.*.cfg"):
            if config_file.is_file():
                config_path = config_file
                break

        if config_path is None:
            return None

        return config_path