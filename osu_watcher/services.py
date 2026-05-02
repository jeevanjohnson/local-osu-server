from jays_tools.architecture import Service
from pathlib import Path
import os
from core.models.adapters.database.osu_file_locations import OsuFileLocations
from osu_watcher.models.domain import ParsedOsuFile
from core.services.osu_file import OsuFileService as BaseOsuFileService


class OsuFileLocationService(Service):
    def remove(self, path: Path, osu_file_locations: OsuFileLocations) -> OsuFileLocations:
        md5 = osu_file_locations.path_to_md5[path]
        beatmap_id = osu_file_locations.path_to_id.get(path)
        beatmap_set_id = osu_file_locations.path_to_set_id.get(path)
        filename = osu_file_locations.path_to_filename[path]

        # path -> x
        del osu_file_locations.path_to_md5[path]
        del osu_file_locations.path_to_filename[path]

        if beatmap_id is not None:
            del osu_file_locations.path_to_id[path]

        if beatmap_set_id is not None:
            del osu_file_locations.path_to_set_id[path]

        # x -> path
        del osu_file_locations.md5_to_path[md5]
        del osu_file_locations.filename_to_path[filename]

        if beatmap_id is not None:
            new_id_to_paths = [
                new_path for new_path in osu_file_locations.id_to_paths[beatmap_id]
                if new_path != path
            ]

            if new_id_to_paths:
                osu_file_locations.id_to_paths[beatmap_id] = new_id_to_paths
            else:
                del osu_file_locations.id_to_paths[beatmap_id]

        if beatmap_set_id is not None:
            new_set_id_to_paths = [
                new_path for new_path in osu_file_locations.set_id_to_paths[beatmap_set_id]
                if new_path != path
            ]

            if new_set_id_to_paths:
                osu_file_locations.set_id_to_paths[beatmap_set_id] = new_set_id_to_paths
            else:
                del osu_file_locations.set_id_to_paths[beatmap_set_id]

        return osu_file_locations

    def add(self, parsed_osu_file: ParsedOsuFile, osu_file_locations: OsuFileLocations) -> OsuFileLocations:
        if parsed_osu_file.beatmap_id is not None:
            if parsed_osu_file.beatmap_id not in osu_file_locations.id_to_paths:
                osu_file_locations.id_to_paths[parsed_osu_file.beatmap_id] = []

            osu_file_locations.id_to_paths[parsed_osu_file.beatmap_id].append(
                parsed_osu_file.path)

        osu_file_locations.md5_to_path[parsed_osu_file.md5] = parsed_osu_file.path
        osu_file_locations.filename_to_path[parsed_osu_file.filename] = parsed_osu_file.path

        if parsed_osu_file.beatmap_set_id is not None:
            if parsed_osu_file.beatmap_set_id not in osu_file_locations.set_id_to_paths:
                osu_file_locations.set_id_to_paths[parsed_osu_file.beatmap_set_id] = [
                ]

            osu_file_locations.set_id_to_paths[parsed_osu_file.beatmap_set_id].append(
                parsed_osu_file.path)

        osu_file_locations.path_to_md5[parsed_osu_file.path] = parsed_osu_file.md5
        osu_file_locations.path_to_filename[parsed_osu_file.path] = parsed_osu_file.filename

        if parsed_osu_file.beatmap_set_id is not None:
            osu_file_locations.path_to_set_id[parsed_osu_file.path] = parsed_osu_file.beatmap_set_id

        if parsed_osu_file.beatmap_id is not None:
            osu_file_locations.path_to_id[parsed_osu_file.path] = parsed_osu_file.beatmap_id

        return osu_file_locations


class OsuDirectoryServce(Service):

    def get_raw_songs_folder_directory_from_config_file(self, raw_confg_file: str) -> str | None:
        for line in raw_confg_file.splitlines():
            line = line.strip()

            if line.startswith("BeatmapDirectory"):
                return line.split("=")[1].strip()

        return None

    def get_path_from_raw_path(self, raw_path: str, osu_directory: Path) -> Path:
        if os.path.isabs(raw_path):
            return Path(raw_path)
        else:
            return osu_directory / raw_path

# TODO: Good architecture?
class OsuFileService(BaseOsuFileService):

    def parse_watcher_data(self, osu_file: Path) -> ParsedOsuFile:
        return ParsedOsuFile(
            beatmap_id=self.get_beatmap_id(osu_file.read_bytes()),
            beatmap_set_id=self.get_beatmap_set_id(osu_file.parent.name),
            md5=self.get_md5(osu_file.read_bytes()),
            filename=osu_file.name,
            path=osu_file.resolve(),
        )
