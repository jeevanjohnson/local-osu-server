import asyncio
from osu_snapshot.usecases import OsuSnapShotUseCase
from jays_tools.services import Service, ReadinessSignal


async def async_start() -> None:
    osu_scraping_use_case = OsuSnapShotUseCase()
    await osu_scraping_use_case.save_recent_snapshot()


def start(readiness_signal: ReadinessSignal) -> None:
    readiness_signal.set()
    asyncio.run(async_start())


def OsuSnapShotService() -> Service:
    return Service(
        name="osu! Snapshot Service",
        description="Service responsible for scraping osu! website and saving snapshots to database.",
        start_func=start,
    )
