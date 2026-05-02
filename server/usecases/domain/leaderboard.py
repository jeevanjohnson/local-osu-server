from jays_tools.architecture import DomainUseCase, Repositories, DomainUseCases
from core.models.adapters.database.beatmaps import Beatmap
from server.adapters.osu_protocol.osu.leaderboard.enums import LeaderboardType
from server.adapters.osu_protocol.osu.leaderboard.leaderboard import Leaderboard
from core.usecases.domain.osu_api import OsuApiV2DomainUseCase
from server.usecases.domain.player import PlayerDomainUseCase
from core.usecases.domain.scores import ScoresDomainUseCase


class LeaderboardDomainUseCases(DomainUseCases):
    osu_api = OsuApiV2DomainUseCase()
    player = PlayerDomainUseCase()


class LeaderboardDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = None
        self.services = None
        self.adapters = None
        self.domain_use_cases = LeaderboardDomainUseCases()

    async def get_personal_best_leaderboard(self, beatmap: Beatmap) -> Leaderboard:
        ...

    async def get_leaderboard(self, beatmap: Beatmap, type: LeaderboardType) -> Leaderboard:
        if type == LeaderboardType.COUNTRY:
            return await self.get_personal_best_leaderboard(beatmap)
        elif type == LeaderboardType.FRIENDS:
            return await self.get_friends_leaderboard(beatmap)
        elif type == LeaderboardType.MODS:
            return await self.get_selected_mods_leaderboard(beatmap)
        else:
            return await self.get_global_leaderboard(beatmap)
