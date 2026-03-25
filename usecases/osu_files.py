import aiohttp

from adapters import log
from adapters.osu_file import OsuFile
from cache import cached_for_10_minutes, cached_for_30_minutes
from constants import OSU_FILES_FILE
from repositories.osu_files import OsuFilesRepository


@cached_for_30_minutes
async def retrive_osu_file_from_web(beatmap_id: int) -> OsuFile | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://osu.ppy.sh/osu/{beatmap_id}") as response:
            if response.status != 200:
                log.warning(
                    f"Failed to retrieve .osu file for beatmap id {beatmap_id}, status code: {response.status}"
                )
                return None

            return OsuFile.from_raw(await response.content.read())


@cached_for_10_minutes
async def get_by_md5(md5: str) -> OsuFile | None:
    osu_files_repo = OsuFilesRepository(OSU_FILES_FILE)
    osu_file = await osu_files_repo.get_by_md5(md5)

    if osu_file is None:
        log.info(f"No osu! file found for MD5 {md5}")
        return

    log.success(f"Found osu! file for MD5 {md5}")

    return osu_file.file


async def store(osu_file: OsuFile, store_audio: bool = False) -> None:
    osu_files_repo = OsuFilesRepository(OSU_FILES_FILE)

    if store_audio:
        log.info(
            f"Storing osu! file and audio for map {osu_file.artist} - {osu_file.title} [{osu_file.version}] (MD5: {osu_file.md5})"
        )
        osu_file.get_audio_file()

    await osu_files_repo.upsert(osu_file.md5, osu_file)

    log.success(
        f"Successfully stored osu! file for map {osu_file.artist} - {osu_file.title} [{osu_file.version}] (MD5: {osu_file.md5})"
    )

    return None
