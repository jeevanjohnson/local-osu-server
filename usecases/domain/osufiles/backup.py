import aiohttp

# from adapters import log
from usecases.adapters.osu_file import OsuFile
from repositories.osufiles.backup import OsuFileBackupRepository
from repositories.osufiles.songs_folder import OsuFileRepository

# @cached_for_30_minutes
async def retrive_osu_file_from_web(beatmap_id: int) -> OsuFile | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://osu.ppy.sh/osu/{beatmap_id}") as response:
            if response.status != 200:
                print(
                    f"Failed to retrieve .osu file for beatmap id {beatmap_id}, status code: {response.status}"
                )
                return None

            return OsuFile.from_raw(await response.content.read())


# @cached_for_10_minutes
async def get_by_md5(md5: str) -> OsuFile | None:
    osu_files_repo = OsuFileRepository()
    osu_file = await osu_files_repo.from_md5(md5)

    if osu_file is None:
        # log.info(f"No osu! file found for MD5 {md5}")
        return

    # log.success(f"Found osu! file for MD5 {md5}")

    return osu_file


async def store(osu_file: OsuFile, store_audio: bool = False) -> None:
    osu_files_repo = OsuFileBackupRepository()

    if store_audio:
        osu_file.get_audio_file()

    await osu_files_repo.save_backup(osu_file)

    return None
