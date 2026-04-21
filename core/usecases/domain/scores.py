from core.repositories.scores import ScoresRepository
from core.models.database.scores import Score

def get_map_scores_for(profile_name: str, beatmap_md5: str) -> list[Score]:
    scores_repo = ScoresRepository()
    map_scores = scores_repo.get_scores_for(profile_name, beatmap_md5)

    return map_scores

def get_personal_best_for(profile_name: str, beatmap_md5: str) -> Score | None:
    scores_repo = ScoresRepository()
    map_scores = scores_repo.get_scores_for(profile_name, beatmap_md5)

    if not map_scores:
        return None

    personal_best = max(map_scores, key=lambda score: score.statistics.score)
    
    return personal_best