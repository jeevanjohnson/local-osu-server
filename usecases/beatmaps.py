from datetime import datetime
from pathlib import Path

import cache
import usecases.songs_folder
from adapters import log, log_time
from constants import BEATMAPS_FILE, OSU_FILES_FILE
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
from models.database.profiles import CurrentSettings
from models.domain.errors import BeatmapNotFoundError
from models.domain.gameplay import osuGameMode
from osuProtocol.client_web import osuMapStatus
from repositories.beatmaps import BeatmapsRepository
from repositories.osu_files import OsuFilesRepository
from usecases.providers import get_ossapi_async
from usecases.songs_folder import (
    DifficultyAdjustedBeatmapResolver,
    OsuFileResolver,
)

_NON_EXPIRING_STATUSES = {
    osuMapStatus.RANKED,
    osuMapStatus.APPROVED,
    osuMapStatus.LOVED,
}


class BeatmapResolver:
    def __init__(
        self,
        songs_folder: Path,
        beatmaps_repo: BeatmapsRepository,
        osu_files_repo: OsuFilesRepository,
        current_settings: CurrentSettings,
    ) -> None:
        self.beatmaps_repo = beatmaps_repo
        self.osu_files_repo = osu_files_repo
        self.current_settings = current_settings
        self.songs_folder = songs_folder
        self.osu_file_resolver = OsuFileResolver(songs_folder)
        self.difficulty_adjusted_beatmap_resolver = DifficultyAdjustedBeatmapResolver(
            songs_folder
        )

    @log_time
    async def from_db(
        self, beatmap_md5: str | None = None, beatmap_id: int | None = None
    ) -> Beatmap | None:
        if beatmap_md5 is not None:
            bmap = cache.beatmap_by_md5.get(beatmap_md5)
            if bmap:
                return bmap

            try:
                bmap = await self.beatmaps_repo.require_by_md5(beatmap_md5)
                cache.beatmap_by_md5.set(beatmap_md5, bmap)
                return bmap
            except BeatmapNotFoundError:
                return None

        if beatmap_id is not None:
            bmap = cache.beatmap_by_id.get(beatmap_id)
            if bmap:
                return bmap

            try:
                bmap = await self.beatmaps_repo.require_by_id(beatmap_id)
                cache.beatmap_by_id.set(beatmap_id, bmap)
                return bmap
            except BeatmapNotFoundError:
                return None

        return None

    @log_time
    async def from_api_md5(
        self, beatmap_md5: str, filename: str | None = None
    ) -> Beatmap | None:
        bmap = cache.beatmap_by_md5.get(beatmap_md5)
        if bmap:
            return bmap

        osuApiAsync = await get_ossapi_async()

        try:
            api_beatmap = await osuApiAsync.beatmap(checksum=beatmap_md5)
        except ValueError as e:
            log.error(
                f"Error fetching beatmap with md5 {beatmap_md5} from osu api: {e}"
            )
            return None

        if api_beatmap is None:
            return None

        # get .osu file from songs folder
        if filename is None:
            osu_file = self.osu_file_resolver.from_set_id_and_md5(
                api_beatmap.beatmapset_id, beatmap_md5
            )
        else:
            osu_file = self.osu_file_resolver.from_set_id_and_filename(
                set_id=api_beatmap.beatmapset_id,
                filename=filename,
            )

        if osu_file is None:
            # Attempt fallback
            log.warning(
                f"Failed to find .osu file for beatmap with md5 {beatmap_md5} using set id hint, attempting full scan by md5"
            )

            osu_file = self.osu_file_resolver.from_md5(beatmap_md5)

        if osu_file is None:
            return None

        beatmap_set = api_beatmap.beatmapset()

        # Seperate README.md
        # one for setup
        # one for features
        # one for philosophy
        # keep main one simple and short with links to the others

        bmap = Beatmap(
            time_inserted=datetime.now(),
            id=api_beatmap.id,
            set_id=api_beatmap.beatmapset_id,
            md5=api_beatmap.checksum or beatmap_md5,
            artist=beatmap_set.artist,
            title=beatmap_set.title,
            difficulty_name=api_beatmap.version,
            max_combo=api_beatmap.max_combo or 0,
            status=osuMapStatus.from_api_v2(api_beatmap.status),
            mode=osuGameMode.from_api_v2(api_beatmap.mode),
            difficulty_adjusted=False,
            play_count=api_beatmap.playcount,
            pass_count=api_beatmap.passcount,
            last_updated=api_beatmap.last_updated,
            average_rating=beatmap_set.rating,
        )

        cache.beatmap_by_md5.set(beatmap_md5, bmap)
        cache.beatmap_by_id.set(bmap.id, bmap)

        if bmap.status.permanent:
            await self.beatmaps_repo.insert_beatmap(bmap)

        return bmap

    @log_time
    async def from_api_id(
        self, beatmap_id: int, filename: str | None = None
    ) -> Beatmap | None:
        osuApiAsync = await get_ossapi_async()

        api_beatmap = await osuApiAsync.beatmap(beatmap_id=beatmap_id)

        if api_beatmap is None:
            return None

        assert api_beatmap.checksum is not None, (
            "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
        )

        if filename is None:
            osu_file = self.osu_file_resolver.from_set_id_and_md5(
                api_beatmap.beatmapset_id, api_beatmap.checksum
            )
        else:
            osu_file = self.osu_file_resolver.from_set_id_and_filename(
                set_id=api_beatmap.beatmapset_id,
                filename=filename,
            )

        if osu_file is None:
            return None

        beatmap_set = api_beatmap.beatmapset()

        bmap = Beatmap(
            time_inserted=datetime.now(),
            id=api_beatmap.id,
            set_id=api_beatmap.beatmapset_id,
            md5=api_beatmap.checksum,
            artist=beatmap_set.artist,
            title=beatmap_set.title,
            difficulty_name=api_beatmap.version,
            max_combo=api_beatmap.max_combo or 0,
            play_count=api_beatmap.playcount,
            pass_count=api_beatmap.passcount,
            last_updated=api_beatmap.last_updated,
            status=osuMapStatus.from_api_v2(api_beatmap.status),
            mode=osuGameMode.from_api_v2(api_beatmap.mode),
            difficulty_adjusted=False,
            average_rating=beatmap_set.rating,
        )

        cache.beatmap_by_md5.set(api_beatmap.checksum, bmap)
        cache.beatmap_by_id.set(bmap.id, bmap)

        if bmap.status.permanent:
            await self.beatmaps_repo.insert_beatmap(bmap)

        return bmap

    @log_time
    def check_hot_cache(self, beatmap_md5: str) -> Beatmap | None:
        """Return a beatmap from the hot cache if present."""
        return cache.beatmap_by_md5.get(beatmap_md5)

    @log_time
    async def find_unsubmitted_map(
        self, beatmap_md5: str, beatmap_set_id: int, map_filename: str
    ) -> Beatmap | None:
        """Retrives an unsubmitted map from songs folder if exists and returns it as a Beatmap model."""
        osu_file = self.osu_file_resolver.from_set_id_and_filename(
            set_id=beatmap_set_id,
            filename=map_filename,
        )
        if osu_file is None:
            osu_file = self.osu_file_resolver.from_md5(beatmap_md5)

        if osu_file is None:
            return None

        if osu_file.unsubmitted:
            unsubmitted_beatmap = Beatmap(
                time_inserted=datetime.now(),
                id=osu_file.beatmap_id,
                set_id=beatmap_set_id,
                md5=beatmap_md5,
                artist=osu_file.artist,
                title=osu_file.title,
                difficulty_name=osu_file.version,
                max_combo=osu_file.max_combo,
                status=osuMapStatus.PENDING,
                mode=osuGameMode.STANDARD,
                difficulty_adjusted=False,
                play_count=0,
                pass_count=0,
                last_updated=datetime.now(),
                average_rating=0.0,
            )

            if unsubmitted_beatmap.status.permanent:
                await self.beatmaps_repo.insert_beatmap(unsubmitted_beatmap)

            return unsubmitted_beatmap

        return None

    @log_time
    async def from_difficulty_adjusted_request(
        self, beatmap_md5: str, beatmap_set_id: int, map_filename: str
    ) -> Beatmap | None:
        difficulty_adjusted_osu_file = (
            self.difficulty_adjusted_beatmap_resolver.from_set_id_and_filename(
                set_id=beatmap_set_id,
                filename=map_filename,
                md5=beatmap_md5,
            )
        )

        if difficulty_adjusted_osu_file is None:
            return None

        original_beatmap = await self.from_db(
            beatmap_id=difficulty_adjusted_osu_file.beatmap_id
        )
        if original_beatmap is None:
            original_beatmap = await self.from_api_id(
                beatmap_id=difficulty_adjusted_osu_file.beatmap_id
            )

        if original_beatmap is None:
            return None

        difficulty_adjusted_beatmap = Beatmap(
            time_inserted=datetime.now(),
            id=original_beatmap.id,
            set_id=original_beatmap.set_id,
            md5=beatmap_md5,
            artist=original_beatmap.artist,
            title=original_beatmap.title,
            difficulty_name=original_beatmap.difficulty_name,
            max_combo=original_beatmap.max_combo,
            status=original_beatmap.status,
            mode=original_beatmap.mode,
            difficulty_adjusted=True,
            play_count=original_beatmap.play_count,
            pass_count=original_beatmap.pass_count,
            last_updated=original_beatmap.last_updated,
            average_rating=original_beatmap.average_rating,
        )

        if difficulty_adjusted_beatmap.status.permanent:
            await self.beatmaps_repo.insert_beatmap(difficulty_adjusted_beatmap)

        return difficulty_adjusted_beatmap

    @log_time
    async def from_leaderboard_request(
        self, beatmap_md5: str, beatmap_set_id: int, map_filename: str
    ) -> Beatmap | None:
        # Phase 1: hot cache
        beatmap = self.check_hot_cache(beatmap_md5)
        if beatmap:
            return beatmap
        else:
            log.warning(
                f"Beatmap with md5 {beatmap_md5} not found in hot cache, proceeding to resolve from disk and API"
            )

        # Phase 2: DB
        beatmap = await self.from_db(beatmap_md5)
        if beatmap:
            return beatmap

        # Phase 3: API
        beatmap = await self.from_api_md5(beatmap_md5, filename=map_filename)
        if beatmap:
            return beatmap

        # Phase 4: Check for unsubmitted map
        unsubmitted_map = await self.find_unsubmitted_map(
            beatmap_md5=beatmap_md5,
            beatmap_set_id=beatmap_set_id,
            map_filename=map_filename,
        )
        if unsubmitted_map is not None:
            return unsubmitted_map

        # Phase 5: Possible difficulty-adjusted Request
        if not self.current_settings.difficulty_adjusted_beatmaps.sync_rank_status_with_bancho:
            return None

        if not usecases.songs_folder.valid_difficulty_adjusted_filename(map_filename):
            return None

        difficulty_adjusted_beatmap = await self.from_difficulty_adjusted_request(
            beatmap_md5=beatmap_md5,
            beatmap_set_id=beatmap_set_id,
            map_filename=map_filename,
        )

        if difficulty_adjusted_beatmap is None:
            log.warning(
                f"Beatmap with md5 {beatmap_md5} and filename {map_filename} is a difficulty-adjusted map but failed to resolve as such."
            )
            return None

        return difficulty_adjusted_beatmap

    @log_time
    async def from_score_submission_request(self, beatmap_md5: str) -> Beatmap | None:
        log.info(f"Score submission resolve start md5={beatmap_md5}")
        # Simpler path for score submissions since we don't have filename or set id hints to resolve from.
        # Just check DB and then API by md5.
        # TODO: Maybe attempt diff adjust via scanning songs folder?
        beatmap = await self.from_db(beatmap_md5)
        if beatmap:
            log.success(
                f"Score submission DB hit md5={beatmap_md5} status={beatmap.status.name}"
            )
            return beatmap

        log.warning(f"Score submission DB miss md5={beatmap_md5}, trying API")
        beatmap = await self.from_api_md5(beatmap_md5)
        if beatmap:
            log.success(
                f"Score submission API hit md5={beatmap_md5} status={beatmap.status.name}"
            )
            return beatmap

        log.warning(f"Score submission resolve failed md5={beatmap_md5}")
        return None


@log_time
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

    return await resolver.from_leaderboard_request(
        beatmap_md5=beatmap_md5,
        beatmap_set_id=beatmap_set_id,
        map_filename=map_filename,
    )


@log_time
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
    return await resolver.from_score_submission_request(beatmap_md5=beatmap_md5)


async def from_md5(
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
    return await resolver.from_api_md5(beatmap_md5=beatmap_md5)
