
from jays_tools.architecture import Adapter
from datetime import datetime, timedelta
from typing import Any
import asyncio

from ossapi import OssapiAsync as BaseOssapiAsync, ScoreType
from ossapi import Cursor as BaseCursor

from core.models.domain.normalizers.mods import Mods
from core.models.domain.osuapi import OsuApiBeatmap, OsuApiScore
from core.models.domain.normalizers.game_mode import GameMode

ONE_MINUTE = timedelta(minutes=1)


class CursorString(str, BaseCursor):
    pass


class OssapiAsync(BaseOssapiAsync):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_calls = 0
        self.last_call_time = datetime.now()

    def check_rate_limit(self) -> None:
        # https://osu.ppy.sh/docs/#terms-of-use

        time_since_last_call = datetime.now() - self.last_call_time
        if time_since_last_call >= ONE_MINUTE:
            self.api_calls = 0
            self.last_call_time = datetime.now()

        if self.api_calls >= 60:
            raise SystemExit(
                "More than 60 API calls in the last minute! Please contact a developer ASAP!!"
            )

        self.api_calls += 1

    async def _request(self, type_, method, url, params=None, data=None) -> Any:
        if params is None:
            params = {}

        if data is None:
            data = {}

        for key, value in params.items():
            if isinstance(value, CursorString):
                params["cursor_string"] = value

                if "cursor" in params:
                    del params["cursor"]

            if key == "mods" and isinstance(value, int):
                raise TypeError(
                    "Legacy mod values are not supported. Please use ossapi.enums.Mod"
                )

        self.check_rate_limit()
        return await super()._request(type_, method, url, params=params, data=data)


class OsuApiV2Adapter(Adapter):
    def get_client(self, client_id: int, client_secret: str) -> OssapiAsync:
        return OssapiAsync(
            client_id=client_id,
            client_secret=client_secret
        )

    async def get_beatmap(
        self,
        client: OssapiAsync,
        beatmap_id: int | None = None,
        checksum: str | None = None,
        filename: str | None = None,
    ) -> OsuApiBeatmap | None:
        if not any((beatmap_id, checksum, filename)):
            raise ValueError(
                "At least one identifier (beatmap_id, checksum, filename) must be provided"
            )

        try:
            beatmap = await client.beatmap(
                beatmap_id=beatmap_id,
                checksum=checksum,
                filename=filename,
            )
        except ValueError:
            return None

        beatmap_set = beatmap.beatmapset()

        assert beatmap.checksum, "Beatmap checksum is required to create OsuApiBeatmap"

        return OsuApiBeatmap.from_api(
            beatmap=beatmap,
            beatmap_set=beatmap_set
        )

    async def get_recent_scores(
        self,
        client: OssapiAsync,
        user_id: int,
        game_mode: GameMode,
        include_fails: bool = True
    ) -> list[OsuApiScore]:
        try:
            recent_scores = await client.user_scores(
                user_id=user_id,
                type=ScoreType.RECENT,
                include_fails=include_fails,
                mode=game_mode.to_api(),
            )
        except ValueError:
            return []

        return [
            OsuApiScore.from_api(score, game_mode)
            for score in recent_scores
        ]

    async def get_replay(
        self,
        client: OssapiAsync,
        score_id: int,
        only_frames: bool = False
    ) -> bytes | None:
        try:
            replay = await client.download_score(
                score_id=score_id
            )
        except ValueError:
            return None

        if not only_frames:
            return replay.pack()

        raise NotImplementedError("Raw replay frames are not yet supported")

    async def get_scores(
        self,
        client: OssapiAsync,
        beatmap: OsuApiBeatmap,
        game_mode: GameMode,
        mods: Mods | None = None,
        limit: int = 100,
        lazer_only: bool = False,
        stable_only: bool = False,
    ) -> list[OsuApiScore]:
        if lazer_only and stable_only:
            raise ValueError(
                "Cannot set both lazer_only and stable_only to True"
            )

        try:
            beatmap_scores = await client.beatmap_scores(
                beatmap_id=beatmap.id,
                mode=game_mode.to_api(),
                limit=limit,
                mods=mods.to_api() if mods else None,
                legacy_only=stable_only,
                # TODO: RankingType?
            )
        except ValueError:
            return []

        scores = [
            OsuApiScore.from_api(score, game_mode)
            for score in beatmap_scores.scores
        ]

        if lazer_only:
            scores = [
                score for score in scores
                if score.lazer
            ]

        return scores[:limit]

    async def get_specific_scores(
        self,
        client: OssapiAsync,
        beatmap: OsuApiBeatmap,
        game_mode: GameMode,
        user_ids: list[int],
        lazer_only: bool = False,
        stable_only: bool = False,
    ) -> list[OsuApiScore]:
        if lazer_only and stable_only:
            raise ValueError(
                "Cannot set both lazer_only and stable_only to True"
            )

        scores_tasks = [
            self.get_user_score(
                client=client,
                beatmap=beatmap,
                game_mode=game_mode,
                user_id=user_id,
                lazer_only=lazer_only,
                stable_only=stable_only,
            )
            for user_id in user_ids
        ]

        scores = [
            score for score in await asyncio.gather(*scores_tasks)
            if score is not None
        ]

        return scores

    async def get_user_score(
        self,
        client: OssapiAsync,
        beatmap: OsuApiBeatmap,
        game_mode: GameMode,
        user_id: int,
        lazer_only: bool = False,
        stable_only: bool = False,
    ) -> OsuApiScore | None:
        if lazer_only and stable_only:
            raise ValueError(
                "Cannot set both lazer_only and stable_only to True"
            )

        try:
            beatmap_user_score = await client.beatmap_user_score(
                beatmap_id=beatmap.id,
                user_id=user_id,
                mode=game_mode.to_api(),
                legacy_only=stable_only,
            )
        except Exception as error:
            if "None" in str(error):
                return None

            raise error

        score = OsuApiScore.from_api(
            beatmap_user_score.score,
            game_mode
        )

        if lazer_only and not score.lazer:
            return None

        return score
