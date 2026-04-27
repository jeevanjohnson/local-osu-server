from core.repositories.database import SQLDatabaseInstance
from core.models.adapters.database.scores import Score
from jays_tools.sql_database import EqualTo
from core.models.domain.normalizers.game_mode import GameMode


class ScoresRepository:
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get_all_scores_for(
        self,
        profile_name: str,
        game_mode: GameMode | None = None
    ) -> list[Score]:
        if game_mode is not None:
            query = EqualTo("profile_name", profile_name) & EqualTo(
                "game_mode", game_mode.value
            )
        else:
            query = EqualTo("profile_name", profile_name)

        return await self.database.find(
            Score, query
        )

    async def get_scores_for_beatmap(self, beatmap_md5: str) -> list[Score]:
        return await self.database.find(
            Score, EqualTo("beatmap_md5", beatmap_md5)
        )

    async def get_score_by_id(self, score_id: int) -> Score | None:
        scores = await self.database.find(
            Score, EqualTo("id", score_id)
        )
        if not scores:
            return None

        return scores[0]

    async def get_map_score_for(self, beatmap_md5: str, profile_name: str) -> Score | None:
        scores = await self.database.find(
            Score,
            EqualTo("beatmap_md5", beatmap_md5) & EqualTo(
                "profile_name", profile_name)
        )
        if not scores:
            return None

        return scores[0]

    async def insert_score(self, score: Score) -> Score:
        return await self.database.insert(score)

    async def delete_score(self, score: Score) -> Score:
        return await self.database.delete(score)
