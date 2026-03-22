from pathlib import Path

from jays_tools import JsonDatabase
from models.database.scores import (
    CurrentScores as Scores,
    CurrentScore as Score,
)


class ScoresRepository:
    def __init__(self, path: Path) -> None:
        self.scores = JsonDatabase(path=path, models=Scores)

    async def get_total_scores(self) -> int:
        async with self.scores as scores:
            return scores.total_scores

    async def save_score(self, score: Score) -> None:
        async with self.scores as scores:
            if score.beatmap.md5 not in scores.scores:
                scores.scores[score.beatmap.md5] = []

            scores.scores[score.beatmap.md5].append(score)

            self.scores.set(scores)
