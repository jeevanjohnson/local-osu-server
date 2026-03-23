from adapters import OsuFile, log
from constants import OSU_FILES_FILE
from repositories.osu_files import OsuFilesRepository


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
