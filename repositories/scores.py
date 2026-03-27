from jays_tools import JsonDatabase

from constants.paths import SCORES
from models.database.scores import (
    CurrentMapScores as MapScores,
)
from models.database.scores import (
    CurrentScore as Score,
)
from models.database.scores import (
    CurrentScores as Scores,
)
from models.database.scores import (
    CurrentScoresForProfile as ScoresForProfile,
)
from osuProtocol.client_web import ScoringAlgorithm
from osuProtocol.server_packets import osuGameMode


class ScoresRepository:
    def __init__(self) -> None:
        self.scores = JsonDatabase(path=SCORES, models=Scores)

    @staticmethod
    def _profile_key(profile_name: str) -> str:
        """Normalize profile name to lowercase for consistent lookups"""
        return profile_name.lower()

    async def allocate_score_id(self) -> int:
        """Atomically allocate next score ID"""
        async with self.scores as scores:
            scores.score_counter += 1
            self.scores.set(scores)
            return scores.score_counter

    async def delete_score_by_id(self, score_id: int) -> None:
        """Delete a score by its unique ID"""
        async with self.scores as scores:
            # Remove from profiles
            for profile_scores in scores.profiles.values():
                for map_scores in profile_scores.scores.values():
                    map_scores.scores = [
                        s for s in map_scores.scores if s.id != score_id
                    ]

            # Remove from beatmap leaderboards
            for map_scores in scores.beatmap_leaderboards.values():
                map_scores.scores = [s for s in map_scores.scores if s.id != score_id]

            self.scores.set(scores)

    async def save_score(self, score: Score, profile_name: str) -> None:
        """
        Save score to both profile index and beatmap leaderboard (atomic).
        Updates both indexes in a single write.
        """
        profile_key = self._profile_key(profile_name)

        async with self.scores as scores:
            # Ensure profile exists
            if profile_key not in scores.profiles:
                scores.profiles[profile_key] = ScoresForProfile()

            # Ensure beatmap entry exists in profile
            if score.beatmap_md5 not in scores.profiles[profile_key].scores:
                scores.profiles[profile_key].scores[score.beatmap_md5] = MapScores(
                    beatmap_md5=score.beatmap_md5,
                    scores=[],
                )

            # Add to profile's beatmap
            scores.profiles[profile_key].scores[score.beatmap_md5].append(score)

            # Ensure beatmap leaderboard exists
            if score.beatmap_md5 not in scores.beatmap_leaderboards:
                scores.beatmap_leaderboards[score.beatmap_md5] = MapScores(
                    beatmap_md5=score.beatmap_md5,
                    scores=[],
                )

            # Add to leaderboard
            scores.beatmap_leaderboards[score.beatmap_md5].append(score)

            # Atomic write
            self.scores.set(scores)

    async def get_scores_for_profile(
        self, profile_name: str
    ) -> ScoresForProfile | None:
        """Get all scores for a specific profile (O(1) lookup)"""
        profile_key = self._profile_key(profile_name)

        async with self.scores as scores:
            return scores.profiles.get(profile_key)

    async def get_leaderboard_for_beatmap(self, beatmap_md5: str) -> MapScores:
        """Get leaderboard (all players) for a beatmap (O(1) lookup)"""
        async with self.scores as scores:
            if beatmap_md5 not in scores.beatmap_leaderboards:
                scores.beatmap_leaderboards[beatmap_md5] = MapScores(
                    beatmap_md5=beatmap_md5,
                    scores=[],
                )
                self.scores.set(scores)

            return scores.beatmap_leaderboards[beatmap_md5]

    async def get_scores_by_profile_and_beatmap_md5(
        self, profile_name: str, beatmap_md5: str
    ) -> MapScores:
        """Get scores for a specific profile on a specific beatmap (O(1) lookup)"""
        profile_key = self._profile_key(profile_name)

        async with self.scores as scores:
            if profile_key not in scores.profiles:
                return MapScores(beatmap_md5=beatmap_md5, scores=[])

            return scores.profiles[profile_key].scores.get(
                beatmap_md5, MapScores(beatmap_md5=beatmap_md5, scores=[])
            )

    async def get_all_scores(
        self,
        scoring_algorithm: ScoringAlgorithm,
        game_mode: osuGameMode | None = None,
        profile_name: str | None = None,
    ) -> list[MapScores]:
        """
        Get all scores, optionally filtered by profile and/or game mode.

        Args:
            scoring_algorithm: How to sort scores
            game_mode: Optional filter by game mode
            profile_name: Optional filter by profile (for stats recalculation)
        """
        async with self.scores as scores:
            # Determine which beatmaps to iterate
            if profile_name:
                profile_key = self._profile_key(profile_name)
                if profile_key not in scores.profiles:
                    return []
                beatmaps_iter = scores.profiles[profile_key].scores.values()
            else:
                beatmaps_iter = scores.beatmap_leaderboards.values()

            # Filter by game mode if specified
            if game_mode is None:
                result = list(beatmaps_iter)
            else:
                result = []
                for map_scores in beatmaps_iter:
                    filtered = MapScores(
                        beatmap_md5=map_scores.beatmap_md5,
                        scores=[
                            s for s in map_scores.scores if s.game_mode == game_mode
                        ],
                    )
                    if filtered.scores:
                        result.append(filtered)

            # Sort each beatmap's scores
            for map_scores in result:
                map_scores.sort(scoring_algorithm)

            return result

    async def total_scores(self) -> int:
        """Get total score count across all profiles"""
        async with self.scores as scores:
            return scores.total_scores

    async def get_score_by_id(self, score_id: int) -> Score | None:
        """Get a score by its unique ID (O(n) lookup)"""
        async with self.scores as scores:
            for profile_scores in scores.profiles.values():
                for map_scores in profile_scores.scores.values():
                    for score in map_scores.scores:
                        if score.id == score_id:
                            return score

        return None
