import ossapi.enums

from core.adapters.osu_api import CursorString, OsuApiV2Adapter, OssapiAsync
from core.models.domain.normalizers.mods import Mods
from core.models.domain.osuapi import OsuApiBeatmap, OsuApiBeatmapSet, OsuApiScore
from core.usecases.domain.server_settings import ServerSettingsDomainUseCase
from jays_tools.architecture import DomainUseCase, Adapters, DomainUseCases
from core.models.domain.normalizers.game_mode import GameMode
from core.adapters.osu_api import InvalidApiCredentialsError


class OsuApiV2Adapters(Adapters):
    osu_api_v2 = OsuApiV2Adapter()


class LowerLevelDomainUseCases(DomainUseCases):
    server_settings = ServerSettingsDomainUseCase()


class OsuApiV2DomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.adapters = OsuApiV2Adapters()
        self.repositories = None
        self.services = None
        self.lower_level_use_cases = LowerLevelDomainUseCases()

    async def get_api_client(self) -> OssapiAsync:
        client_id = await self.lower_level_use_cases.server_settings.get_osu_api_v2_client_id()
        client_secret = await self.lower_level_use_cases.server_settings.get_osu_api_v2_client_secret()

        if client_id is None or client_secret is None:
            raise InvalidApiCredentialsError(
                "osu! API v2 client ID and secret must be set in server settings"
            )

        return self.adapters.osu_api_v2.get_client(client_id, client_secret)

    async def get_beatmap_from_id(self, beatmap_id: int) -> OsuApiBeatmap | None:
        client = await self.get_api_client()
        return await self.adapters.osu_api_v2.get_beatmap(
            client,
            beatmap_id
        )

    async def get_beatmap_from_md5(self, beatmap_md5: str) -> OsuApiBeatmap | None:
        client = await self.get_api_client()
        return await self.adapters.osu_api_v2.get_beatmap(
            client,
            checksum=beatmap_md5
        )

    async def get_beatmap_from_filename(self, beatmap_filename: str) -> OsuApiBeatmap | None:
        client = await self.get_api_client()
        return await self.adapters.osu_api_v2.get_beatmap(
            client,
            filename=beatmap_filename
        )

    async def get_recent_scores(
        self,
        user_id: int,
        game_mode: GameMode,
        include_fails: bool = True
    ) -> list[OsuApiScore]:
        client = await self.get_api_client()
        return await self.adapters.osu_api_v2.get_recent_scores(
            client,
            user_id,
            game_mode,
            include_fails
        )

    async def get_replay(
        self,
        score_id: int,
    ) -> bytes | None:
        client = await self.get_api_client()
        return await self.adapters.osu_api_v2.get_replay(
            client,
            score_id
        )

    async def get_scores(
        self,
        beatmap: OsuApiBeatmap,
        game_mode: GameMode,
        mods: Mods | None = None,
        limit: int = 100,
        lazer_only: bool = False,
        stable_only: bool = False,
    ) -> list[OsuApiScore]:
        client = await self.get_api_client()
        return await self.adapters.osu_api_v2.get_scores(
            client,
            beatmap,
            game_mode,
            mods,
            limit,
            lazer_only,
            stable_only
        )

    async def get_specific_scores(
        self,
        client: OssapiAsync,
        beatmap: OsuApiBeatmap,
        game_mode: GameMode,
        user_ids: list[int],
        lazer_only: bool = False,
        stable_only: bool = False,
    ) -> list[OsuApiScore]:
        return await self.adapters.osu_api_v2.get_specific_scores(
            client,
            beatmap,
            game_mode,
            user_ids,
            lazer_only,
            stable_only
        )

    async def get_user_score(
        self,
        client: OssapiAsync,
        beatmap: OsuApiBeatmap,
        game_mode: GameMode,
        user_id: int,
        lazer_only: bool = False,
        stable_only: bool = False,
    ) -> OsuApiScore | None:
        return await self.adapters.osu_api_v2.get_user_score(
            client,
            beatmap,
            game_mode,
            user_id,
            lazer_only,
            stable_only
        )

    async def search_beatmaps(
        self,
        query: str,
        category: ossapi.enums.BeatmapsetSearchCategory,
        mode: ossapi.enums.BeatmapsetSearchMode,
        cursor: CursorString | None = None
    ) -> list[OsuApiBeatmapSet]:
        client = await self.get_api_client()
        return await self.adapters.osu_api_v2.search_beatmaps(
            client,
            query,
            category,
            mode,
            cursor
        )

    def osu_direct_to_api_category(
        self,
        direct_category: int
    ) -> ossapi.enums.BeatmapsetSearchCategory:
        return self.adapters.osu_api_v2.osu_direct_to_api_category(direct_category)

    def osu_direct_to_api_game_mode(
        self,
        direct_mode: int
    ) -> ossapi.enums.BeatmapsetSearchMode:
        return self.adapters.osu_api_v2.osu_direct_to_api_game_mode(direct_mode)
