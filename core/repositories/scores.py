from jays_tools import JsonCollection, JsonDatabase
from core.models.database.scores import MapScores, ScoreLookUp, Score
from core.constants import SCORES, SCORES_LOOKUP
from typing import TypedDict
from core.models.domain.gameplay.game_mode import GameMode

class AllMapScoresForProfileResult(TypedDict):
    beatmap_md5: str
    scores: list[Score]

class ScoresRepository:
    def __init__(self) -> None:
        self.collection = JsonCollection(
            path=SCORES,
            model=MapScores
        )

        self.database  = JsonDatabase(
            path=SCORES_LOOKUP,
            database_model=ScoreLookUp
        )
    
    def get_all(self) -> dict[str, MapScores]:
        return self.collection.get_all()
    
    def get_scores(self, beatmap_md5: str) -> MapScores | None:
        if not self.collection.exists(beatmap_md5):
            return None
        
        database =  self.collection.get(beatmap_md5)

        return database.get_database()

    def get_score(self, score_id: int) -> Score | None:
        score_lookup = self.database.get_database()
        
        if score_id not in score_lookup.id_to_beatmap_md5:
            return None

        beatmap_md5 = score_lookup.id_to_beatmap_md5[score_id]

        map_scores = self.get_scores(beatmap_md5)

        if map_scores is None:
            return None

        for score in map_scores.all:
            if score.id == score_id:
                return score
        
        return None

    def generate_new_score_id(self) -> int:
        score_lookup = self.database.get_database()
        existing_ids = set(score_lookup.id_to_beatmap_md5.keys())

        new_id = 1
        while new_id in existing_ids:
            new_id += 1
        
        return new_id

    def get_all_map_scores_for_profile(self, profile_name: str, game_mode: GameMode) -> list[AllMapScoresForProfileResult]:
        score_lookup = self.database.get_database()
        print(f"[REPO_GET_SCORES] Available profile names in database: {list(score_lookup.profile_name_to_ids.keys())}")
        print(f"[REPO_GET_SCORES] Looking for: '{profile_name}'")
        
        if profile_name not in score_lookup.profile_name_to_ids:
            print(f"[REPO_GET_SCORES] ❌ Profile '{profile_name}' NOT found in database!")
            return []

        score_ids = score_lookup.profile_name_to_ids[profile_name]
        print(f"[REPO_GET_SCORES] ✓ Found {len(score_ids)} score IDs for profile '{profile_name}'")
        scores = [self.get_score(score_id) for score_id in score_ids]

        beatmap_md5_to_scores: dict[str, list[Score]] = {}

        for score in scores:
            if score is None:
                continue

            if score.game_mode != game_mode:
                continue
            
            beatmap_md5 = score.beatmap.original_md5

            if beatmap_md5 not in beatmap_md5_to_scores:
                beatmap_md5_to_scores[beatmap_md5] = []
            
            beatmap_md5_to_scores[beatmap_md5].append(score)
        
        return [
            AllMapScoresForProfileResult(
                beatmap_md5=beatmap_md5,
                scores=scores
            )
            for beatmap_md5, scores in beatmap_md5_to_scores.items()
        ]

    def get_all_scores_for(self, profile_name: str) -> list[Score]:
        score_lookup = self.database.get_database()
        
        if profile_name not in score_lookup.profile_name_to_ids:
            return []

        score_ids = score_lookup.profile_name_to_ids[profile_name]
        scores = [self.get_score(score_id) for score_id in score_ids]

        return [score for score in scores if score is not None]

    def get_scores_for(self, profile_name: str, beatmap_md5: str) -> list[Score]:
        map_scores = self.get_scores(beatmap_md5)

        if map_scores is None:
            return []

        profile_scores = [score for score in map_scores.all if score.profile_name == profile_name]

        return profile_scores

    def add_score(self, beatmap_md5: str, score: Score) -> Score:
        # Get the current scores for the beatmap, or create a new MapScores if it doesn't exist
        map_scores = self.get_scores(beatmap_md5)

        if map_scores is None:
            map_scores = MapScores(
                all=[score]
            )
        else:
            map_scores.all.append(score)

        # Update the collection with the new MapScores
        self.collection.update(beatmap_md5, map_scores)

        # Update the score lookup database
        score_lookup = self.database.get_database()
        score_lookup.id_to_beatmap_md5[score.id] = beatmap_md5
        if score.profile_name not in score_lookup.profile_name_to_ids:
            score_lookup.profile_name_to_ids[score.profile_name] = []
        score_lookup.profile_name_to_ids[score.profile_name].append(score.id)
        self.database.update_database(score_lookup)

        return score