from core.models.domain.gameplay.scoring import ScoringType
from core.repositories.scores import ScoresRepository
from core.models.database.scores import Score
from core.models.domain.gameplay.mods import Mods

def get_map_scores_for(profile_name: str, beatmap_md5: str) -> list[Score]:
    scores_repo = ScoresRepository()
    map_scores = scores_repo.get_scores_for(profile_name, beatmap_md5)

    return map_scores

def get_personal_best_for(
    profile_name: str, 
    beatmap_md5: str,
    scoring_type: ScoringType,
    with_mods: Mods | None = None,
) -> Score | None:
    scores_repo = ScoresRepository()
    map_scores = scores_repo.get_scores_for(profile_name, beatmap_md5)

    if with_mods is not None:
        map_scores = [score for score in map_scores if score.mods == with_mods]

    if not map_scores:
        return None

    def score_sort_key(score: Score):
        if scoring_type == ScoringType.SCOREV1:
            return score.statistics.total_score.v1
        elif scoring_type == ScoringType.SCOREV2:
            return score.statistics.total_score.v2
        else:
            return score.pp

    personal_best = max(map_scores, key=score_sort_key)
    
    return personal_best