import asyncio

from jays_tools.architecture import DomainUseCase, UseCase, Adapters, Repositories, Services
from osu_snapshot.services import OsuScraperService, OsuEstimatorService
from core.repositories.osu_snapshots import OsuSnapshotRepository
from osu_snapshot.adapters import OsuWebsiteAdapter
from core.models.adapters.database.snapshots import SnapShot


class OsuSnapShotAdapters(Adapters):
    website = OsuWebsiteAdapter()


class OsuSnapShotRepositories(Repositories):
    snapshots = OsuSnapshotRepository()


class OsuSnapShotServices(Services):
    scraper = OsuScraperService()
    estimator = OsuEstimatorService()


class OsuSnapShotDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.adapters = OsuSnapShotAdapters()
        self.repositories = OsuSnapShotRepositories()
        self.services = OsuSnapShotServices()

    async def get_total_user(self) -> int:
        home_page_html = await self.adapters.website.get_home_page()
        total_registered_users = self.services.scraper.get_total_registered_users(
            home_page_html)
        return total_registered_users

    async def scrape_pp_and_ranks(self, mode: str) -> list[tuple[int, int]]:
        pp_and_ranks = []

        for page in range(1, 201):
            ranking_page_html = await self.adapters.website.get_ranking_page(
                page=page,
                game_mode=mode
            )
            pp_and_ranks.extend(
                self.services.scraper.extract_pp_and_ranks(ranking_page_html))
            print(
                f"Scraped {len(pp_and_ranks)} pp and rank pairs from page {page}/200 of {mode} mode."
            )
            # be nice to the server and avoid rate limits
            await asyncio.sleep(2)

        return pp_and_ranks

    async def generate_synthetic_pp_and_ranks(
        self, known_pp_and_ranks: list[tuple[int, int]],
        total_users: int
    ) -> list[tuple[int, int]]:
        synthetic_pp_and_ranks = self.services.estimator.generate_synthetic_pp_and_ranks(
            known_pp_and_ranks, total_users
        )

        return synthetic_pp_and_ranks

    async def save_snapshot(self, snapshot: SnapShot) -> SnapShot:
        saved_snapshot = await self.repositories.snapshots.save_snapshot(snapshot)
        return saved_snapshot

    async def create_snapshot(self) -> SnapShot:
        new_snapshot = await self.repositories.snapshots.create_snapshot()
        return new_snapshot


class OsuSnapShotDomainUseCases:
    snapshot = OsuSnapShotDomainUseCase()


class OsuSnapShotUseCase(UseCase):
    def __init__(self) -> None:
        self.domains = OsuSnapShotDomainUseCases()

    async def save_recent_snapshot(self) -> None:
        total_registered_users = await self.domains.snapshot.get_total_user()
        print(f"Total registered users: {total_registered_users}")

        snapshot = await self.domains.snapshot.create_snapshot()

        for mode in ["osu", "taiko", "fruits", "mania"]:
            pp_and_ranks = await self.domains.snapshot.scrape_pp_and_ranks(mode)

            synthetic_pp_and_ranks = await self.domains.snapshot.generate_synthetic_pp_and_ranks(
                pp_and_ranks, total_registered_users
            )

            pp_and_ranks.extend(synthetic_pp_and_ranks)

            if mode == "osu":
                snapshot.osu.extend(pp_and_ranks)
            elif mode == "taiko":
                snapshot.taiko.extend(pp_and_ranks)
            elif mode == "fruits":
                snapshot.catch.extend(pp_and_ranks)
            elif mode == "mania":
                snapshot.mania.extend(pp_and_ranks)

            print(
                f"Total pp and rank pairs for {mode} mode: {len(pp_and_ranks)}")

        saved_snapshot = await self.domains.snapshot.save_snapshot(snapshot)

        print(
            f"Saved snapshot with {len(saved_snapshot.osu)} osu pp and rank pairs, "
            f"{len(saved_snapshot.taiko)} taiko pp and rank pairs, "
            f"{len(saved_snapshot.catch)} catch pp and rank pairs, and "
            f"{len(saved_snapshot.mania)} mania pp and rank pairs."
        )
