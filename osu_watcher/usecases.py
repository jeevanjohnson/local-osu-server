import os

from osu_watcher.adapters import OsuClientAdapter, OsuDirectoryAdapter
from osu_watcher.services import OsuDirectoryServce, OsuFileService, OsuFileLocationService
from jays_tools.architecture import DomainUseCase
from core.repositories.osu_file_locations import OsuFileLocationsRepository
from pathlib import Path
import time
from core.models.adapters.database.osu_file_locations import OsuFileLocations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable
from jays_tools.architecture import Adapters, Services, Repositories, UseCases


class OsuDomainAdapters(Adapters):
    osu_client = OsuClientAdapter()
    osu_directory = OsuDirectoryAdapter()


class OsuDomainServices(Services):
    osu_directory = OsuDirectoryServce()
    osu_file_service = OsuFileService()
    osu_file_location = OsuFileLocationService()


class OsuDomainRepositories(Repositories):
    osu_file_locations = OsuFileLocationsRepository()


class OsuDomainUsecases(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = OsuDomainRepositories()
        self.services = OsuDomainServices()
        self.adapters = OsuDomainAdapters()

    def add_osu_files(
        self,
        osu_file_locations: OsuFileLocations,
        osu_files: Iterable[Path]
    ) -> OsuFileLocations:
        # max_workers=8
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.services.osu_file_service.parse_watcher_data, file): file
                for file in osu_files
            }

            for future in as_completed(futures):
                response = future.result()

                self.services.osu_file_location.add(
                    response, osu_file_locations
                )

                print(f"Added {response.path} to database")

        return osu_file_locations

    def delete_osu_files(
        self,
        osu_file_locations: OsuFileLocations,
        osu_files: Iterable[Path]
    ) -> OsuFileLocations:
        for osu_file_path in osu_files:
            osu_file_locations = self.services.osu_file_location.remove(
                osu_file_path, osu_file_locations
            )

        return osu_file_locations

    def sync(
        self,
        osu_file_locations: OsuFileLocations,
        add_osu_files: Iterable[Path] | None,
        delete_osu_files: Iterable[Path] | None,
    ) -> OsuFileLocations:

        if delete_osu_files is not None:
            osu_file_locations = self.delete_osu_files(
                osu_file_locations, delete_osu_files
            )

        if add_osu_files is not None:
            osu_file_locations = self.add_osu_files(
                osu_file_locations, add_osu_files
            )

        return osu_file_locations

    async def is_songs_folder_initilized_in_database(self) -> bool:
        if await self.repositories.osu_file_locations.get() is None:
            return False

        return True

    async def init_songs_folder_in_database(self, songs_folder: Path) -> None:
        osu_file_locations = await self.repositories.osu_file_locations.create()

        osu_file_locations = self.sync(
            osu_file_locations,
            add_osu_files=songs_folder.glob("**/*.osu"),
            delete_osu_files=None
        )

        await self.repositories.osu_file_locations.update(osu_file_locations)

    async def refresh_osu_file_locations_in_database(self, songs_folder: Path) -> None:
        osu_file_locations = await self.repositories.osu_file_locations.get()
        if osu_file_locations is None:
            raise Exception("Songs folder not initialized in database")

        current_songs_folder = set(songs_folder.glob("**/*.osu"))
        all_currently_stored_paths = osu_file_locations.path_to_filename.keys()

        # In DB but not in folder
        files_needing_to_be_deleted = all_currently_stored_paths - current_songs_folder
        # In folder but not in DB
        files_needing_to_be_added = current_songs_folder - all_currently_stored_paths

        osu_file_locations = self.sync(
            osu_file_locations,
            add_osu_files=files_needing_to_be_added,
            delete_osu_files=files_needing_to_be_deleted
        )

        await self.repositories.osu_file_locations.update(osu_file_locations)

    def get_songs_folder_from_running_client(self) -> Path | None:
        # TODO: custom exception handling?
        try:
            osu_directory = self.adapters.osu_client.get_osu_directory()
        except Exception:
            return None

        config_file = self.adapters.osu_directory.get_config_file(
            osu_directory
        )

        if config_file is None:
            raise Exception("couldn't find cfg file")

        raw_songs_folder = self.services.osu_directory.get_raw_songs_folder_directory_from_config_file(
            raw_confg_file=config_file.read_text(errors="ignore")
        )

        if raw_songs_folder is None:
            raise Exception("Couldn't find songs folder in cfg file")

        return self.services.osu_directory.get_path_from_raw_path(
            raw_songs_folder,
            osu_directory
        )

    def wait_till_song_folder_is_avaliable(self) -> Path:
        while True:
            songs_folder = self.get_songs_folder_from_running_client()
            if songs_folder is None:
                time.sleep(1)
                continue

            return songs_folder
