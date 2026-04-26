
import asyncio

from jays_tools.services import Service, ReadinessSignal
from osu_watcher.usecases import OsuDomainUsecases

from osu_watcher.watchdog import SongFolderHandler
from osu_watcher.adapters import AIOWatchdog


async def async_start(readiness_signal: ReadinessSignal) -> None:
    osu_domain_usecases = OsuDomainUsecases()
    print("Waiting for osu! to start")
    songs_folder = osu_domain_usecases.wait_till_song_folder_is_avaliable()

    if not await osu_domain_usecases.is_songs_folder_initilized_in_database(songs_folder):
        print("Initializing osu! file locations...")
        await osu_domain_usecases.init_songs_folder_in_database(songs_folder)
    else:
        print("Refreshing osu! file locations...")
        await osu_domain_usecases.refresh_osu_file_locations_in_database(songs_folder)

    watch = AIOWatchdog(
        path=str(songs_folder),
        event_handler=SongFolderHandler(),
        recursive=True,
    )
    watch.start()
    readiness_signal.set()

    while True:
        await asyncio.sleep(1)


def start(readiness_signal: ReadinessSignal) -> None:
    asyncio.run(async_start(readiness_signal))


def OsuWatcherService() -> Service:
    return Service(
        name="Osu! Watcher",
        description="Records all osu! files in the songs folder",
        start_func=start,
    )
