from datetime import datetime, timedelta
import time
import re
import functools

from core.repositories.beatmaps import BeatmapRepository
from core.repositories.osu_file_locations import OsuFileLocationRepository
from core.models.adapters.database.beatmaps import Beatmap
import core.usecases.domain.osu_api as osu_api_usecases
from core.models.domain.gameplay.game_mode import GameMode
from core.models.domain.gameplay.rank_status import RankStatus
from pathlib import Path
import core.usecases.adapters.osufile as osufile_usecases

from core.usecases.domain.osu_api import OsuApiV2DomainUseCase
from jays_tools.architecture import DomainUseCase, Services, DomainUseCases, Repositories
from core.repositories.beatmaps import BeatmapRepository
from core.repositories.osu_file_locations import OsuFileLocationsRepository
from core.services.osu_file import OsuFileService

FILENAME_REGEX = re.compile(
    r"(?P<artist>.*) - (?P<song_name>.*) ((?P<mapper>.*) \[)(?P<diff_name>.*)\]\.osu"
)
DIFFICULTY_ADJUSTED_REGEX = re.compile(
    r"(?P<rate>[0-9]{1,2}(?:\.[0-9]{1,2})?x) \((?P<bpm>[0-9]+bpm)\)"
)
ATTRIBUTE_EDIT_REGEX = re.compile(
    r"(.*) (HP|CS|AR|OD)([0-9]{1,2}(?:\.[0-9]{1,2})?)"
)


class BeatmapDomainServices(Services):
    osu_file = OsuFileService()


class BeatmapDomainUseCases(DomainUseCases):
    osu_api = OsuApiV2DomainUseCase()


class BeatmapDomainRepositories(Repositories):
    beatmaps = BeatmapRepository()
    osu_file_locations = OsuFileLocationsRepository()


class BeatmapDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.adapters = None
        self.repositories = BeatmapDomainRepositories()
        self.services = BeatmapDomainServices()
        self.lower_level_domain_usecases = BeatmapDomainUseCases()

    @functools.cache
    def is_difficulty_adjusted(self, filename: str) -> bool:
        file_name_data = FILENAME_REGEX.search(filename)
        if not file_name_data:
            return False

        difficulty_name = file_name_data["diff_name"]
        if not difficulty_name:
            return False

        has_rate_adjust = bool(
            DIFFICULTY_ADJUSTED_REGEX.search(difficulty_name)
        )
        has_attribute_adjust = bool(
            ATTRIBUTE_EDIT_REGEX.search(difficulty_name)
        )

        # Accept either type of adjustment: rate-only (e.g. 0.89x (240bpm))
        # or explicit stat edits (AR/CS/HP/OD).
        return has_rate_adjust or has_attribute_adjust

    async def osu_file_to_md5(self, osu_file: Path) -> str | None:
        osu_file_locations = await self.repositories.osu_file_locations.get()
        if osu_file_locations is None:
            raise Exception("Songs folder not initialized in database")

        return osu_file_locations.path_to_md5.get(osu_file)

    async def osu_file_from_md5(self, md5: str) -> Path | None:
        osu_file_locations = await self.repositories.osu_file_locations.get()
        if osu_file_locations is None:
            raise Exception("Songs folder not initialized in database")

        return osu_file_locations.md5_to_path.get(md5)

    async def osu_file_from_filename(self, filename: str) -> Path | None:
        osu_file_locations = await self.repositories.osu_file_locations.get()
        if osu_file_locations is None:
            raise Exception("Songs folder not initialized in database")

        return osu_file_locations.filename_to_path.get(filename)

    async def osu_files_from_id(self, beatmap_id: int) -> list[Path] | None:
        osu_file_locations = await self.repositories.osu_file_locations.get()
        if osu_file_locations is None:
            raise Exception("Songs folder not initialized in database")

        paths = osu_file_locations.id_to_paths.get(beatmap_id)
        if paths is None:
            return None

        return paths

    async def is_unsubmitted(self, md5: str) -> bool:
        path = await self.osu_file_from_md5(md5)
        if path is None:
            raise ValueError(
                "Beatmap with given MD5 not found in osu file locations"
            )

        beatmap_id = self.services.osu_file.get_beatmap_id(
            path.read_bytes()
        )
        beatmap_set_id = self.services.osu_file.get_beatmap_set_id(
            path.parent.name
        )

        if beatmap_id is None:
            return True

        if beatmap_set_id is None:
            return True

        if beatmap_id == 0:
            return True

        if beatmap_set_id == 0:
            return True

        return False

    async def insert_beatmap_in_database(self, beatmap: Beatmap) -> Beatmap:
        return await self.repositories.beatmaps.insert(beatmap)

    async def get_difficulty_adjusted_beatmap(self, md5: str, filename: str) -> Beatmap | None:
        difficulty_adjusted_osu_file = await self.osu_file_from_filename(filename)
        if difficulty_adjusted_osu_file is None:
            return None

        raw_difficulty_adjusted_osu_file = difficulty_adjusted_osu_file.read_bytes()
        ar = self.services.osu_file.get_ar(raw_difficulty_adjusted_osu_file)
        cs = self.services.osu_file.get_cs(raw_difficulty_adjusted_osu_file)
        hp = self.services.osu_file.get_hp(raw_difficulty_adjusted_osu_file)
        od = self.services.osu_file.get_od(raw_difficulty_adjusted_osu_file)
        original_beatmap_id = self.services.osu_file.get_beatmap_id(
            raw_difficulty_adjusted_osu_file
        )

        if (
            ar is None or
            cs is None or
            hp is None or
            od is None or
            original_beatmap_id is None
        ):
            return None

        osu_files = await self.osu_files_from_id(original_beatmap_id)
        if osu_files is None:
            return None

        original_osu_file = [
            osu_file for osu_file in osu_files
            if not self.is_difficulty_adjusted(osu_file.name)
        ]

        if not original_osu_file:
            return None

        original_osu_file = original_osu_file[0]

        original_md5 = await self.osu_file_to_md5(original_osu_file)
        if original_md5 is None:
            return None

        original_beatmap = await self.get_beatmap(original_md5)
        if original_beatmap is None:
            return None

        difficulty_adjusted_beatmap = Beatmap(
            md5=md5,
            id=original_beatmap.id,
            set_id=original_beatmap.set_id,
            artist=original_beatmap.artist,
            title=original_beatmap.title,
            version=filename,
            difficulty_adjusted=True,
            original_beatmap_md5=original_md5,
            max_combo=original_beatmap.max_combo,
            mode=original_beatmap.mode,
            status=original_beatmap.status,
            status_override={},
            ar=ar,
            cs=cs,
            hp=hp,
            od=od,
            # object_count=self.services.osu_file.get_object_count(
            #     difficulty_adjusted_osu_file.read_bytes()
            # ),
            # drain_time_seconds=self.services.osu_file.get_drain_time_seconds(
            #     difficulty_adjusted_osu_file.read_bytes()
            # ),
            play_count=original_beatmap.play_count,
            pass_count=original_beatmap.pass_count,
            pass_count_timestamp=datetime.now(),
            play_count_timestamp=datetime.now(),
            last_updated=original_beatmap.last_updated,
        )

        await self.insert_beatmap_in_database(difficulty_adjusted_beatmap)

        return difficulty_adjusted_beatmap

    async def get_beatmap(self, md5: str) -> Beatmap | None:
        beatmap = await self.get_beatmap_from_database(md5)
        if beatmap is not None:
            return beatmap

        beatmap = await self.get_beatmap_from_api_md5(md5)
        if beatmap is not None:
            await self.insert_beatmap_in_database(beatmap)

        return beatmap

    async def get_beatmap_from_database(self, md5: str) -> Beatmap | None:
        return await self.repositories.beatmaps.get(md5)

    async def get_beatmap_from_api_md5(self, md5: str) -> Beatmap | None:
        osu_api_beatmap = await self.lower_level_domain_usecases.osu_api.get_beatmap_from_md5(md5)
        if osu_api_beatmap is None:
            return None

        return Beatmap(
            md5=md5,
            id=osu_api_beatmap.id,
            set_id=osu_api_beatmap.set_id,
            artist=osu_api_beatmap.artist,
            title=osu_api_beatmap.title,
            version=osu_api_beatmap.difficulty_name,
            difficulty_adjusted=False,
            original_beatmap_md5=md5,
            max_combo=osu_api_beatmap.max_combo,
            mode=osu_api_beatmap.mode,
            status=osu_api_beatmap.status,
            status_override={},
            ar=osu_api_beatmap.ar,
            cs=osu_api_beatmap.cs,
            hp=osu_api_beatmap.hp,
            od=osu_api_beatmap.od,
            # object_count=osufile_usecases.get_object_count_by_md5(md5),
            # drain_time_seconds=osufile_usecases.get_drain_time_seconds_by_md5(
            #     md5),
            play_count=osu_api_beatmap.play_count,
            pass_count=osu_api_beatmap.pass_count,
            pass_count_timestamp=datetime.now(),
            play_count_timestamp=datetime.now(),
            last_updated=osu_api_beatmap.last_updated,
        )
