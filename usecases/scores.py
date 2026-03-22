from repositories.scores import ScoresRepository
from constants import SCORES_FILE

def generate_score_id() -> int:
    scores_repo = ScoresRepository(SCORES_FILE)

    return scores_repo.get_total_scores() + 1