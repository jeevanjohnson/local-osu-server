from core.models.database.profile import ProfileSettings
from core.models.domain.gameplay.scoring import ScoringType
from core.models.database.beatmaps import Beatmap
from core.repositories.scores import ScoresRepository, AllMapScoresForProfileResult
from core.models.database.scores import Score
from core.models.domain.gameplay.mods import Mods
from core.models.domain.gameplay.game_mode import GameMode
import ossapi.models
import core.usecases.domain.calculator.position as score_position_calculator_usecases
import core.usecases.domain.beatmap as domain_beatmap_usecases
import core.usecases.application.score_ranking as score_ranking_usecases
import core.usecases.domain.osu_api as osu_api_usecases
from core.osu_protocol.osu.score_submission import ScoreData
import core.usecases.domain.osu_api as osu_api_usecases
import ossapi.enums
import asyncio
import numpy as np
from scipy.interpolate import RBFInterpolator

async def calculate_total_score_v1(
    beatmap: Beatmap,
    count300: int,
    count100: int,
    count50: int,
    count_miss: int,
    combo: int,
    mods: Mods,
    game_mode: GameMode
) -> int:
    api_client = osu_api_usecases.get_api_client()
    
    try:
        tasks = [
            api_client.beatmap_scores(
                beatmap_id=beatmap.osu_id,
                mode=game_mode.to_api_v2(),
                legacy_only=True,
                type=ossapi.enums.RankingType.SCORE,
            ),
            api_client.beatmap_scores(
                beatmap_id=beatmap.osu_id,
                mode=game_mode.to_api_v2(),
                legacy_only=False,
                type=ossapi.enums.RankingType.SCORE,
                mods=mods.to_stable_mods(),
            )
        ]

        first_scores, second_scores = await asyncio.gather(*tasks)
    except ValueError:
        # if the beatmap doesn't exist on the API, we can't calculate a scorev1 value
        return 0
    
    if not first_scores.scores and not second_scores.scores:
        return 0

    scores_dict = {
        (s.user_id, s.ended_at.timestamp()): s 
        for s in first_scores.scores + second_scores.scores
    }
    scores = list(scores_dict.values())

    # Strategy 1: Few scores - use linear average
    if len(scores) < 4:
        avg_score = np.mean([s.total_score for s in scores])
        return max(1, int(avg_score * 0.95))  # Conservative estimate
    
    # Strategy 2: Medium scores - use closest match
    if len(scores) < 7:
        query_accuracy = (count300 + count100/3 + count50/5) / (count300 + count100 + count50 + count_miss) if (count300 + count100 + count50 + count_miss) > 0 else 0
        
        closest_score = min(
            scores,
            key=lambda s: abs(
                ((s.statistics.great or 0) + (s.statistics.ok or 0)/3 + (s.statistics.meh or 0)/5) 
                / max(1, (s.statistics.great or 0) + (s.statistics.ok or 0) + (s.statistics.meh or 0) + (s.statistics.miss or 0))
                - query_accuracy
            )
        )
        return max(1, int(closest_score.total_score * 0.98))
    
    # Strategy 3: Enough scores - use RBF interpolation
    input_parameters = np.array([
        [
            score.statistics.great or 0,
            score.statistics.ok or 0,
            score.statistics.meh or 0,
            score.statistics.miss or 0,
            score.max_combo or 0,
            Mods.from_api_v2(score.mods).multiplier(game_mode)
        ]
        for score in scores
    ])

    output_scores = np.array(
        [score.total_score for score in scores]
    )

    log_output_scores = np.log(np.maximum(output_scores, 1))

    try:
        rbf_interpolator = RBFInterpolator(
            input_parameters, 
            log_output_scores,
            kernel="multiquadric",
            epsilon=1.0,
            smoothing=1e-3
        )

        query = np.array([
            float(count300), 
            float(count100), 
            float(count50), 
            float(count_miss), 
            float(combo), 
            mods.multiplier(game_mode)
        ])

        log_estimated_score = rbf_interpolator([query])[0]
        estimated_score = np.exp(log_estimated_score)

        return max(1, int(estimated_score))
    except Exception as e:
        print(f"RBF interpolation failed: {e}")
        return 0

def calculate_total_score_v2(
    count300: int,
    count100: int,
    count50: int,
    count_miss: int,
    combo: int,
    beamtap_max_combo: int,
    mods: Mods,
    game_mode: GameMode
) -> int:
        total_hits = count300 + count100 + count50 + count_miss

        if total_hits == 0:
            return 0

        # Accuracy calculation (standard osu! weighting)
        accuracy = (count300 + count100 / 3 + count50 / 5) / total_hits

        # Combo progress: achieved combo / max possible combo
        combo_progress = combo / beamtap_max_combo if beamtap_max_combo > 0 else 0

        # Accuracy progress: in osu!standard this is always 1.0
        accuracy_progress = 1.0

        # Correct lazer scoring formula (two 500k terms)
        hit_score = (
            500_000 * accuracy * combo_progress
            + 500_000 * (accuracy**5) * accuracy_progress
        )

        # Apply the 0.96× "Classic" multiplier (always present for imported scores)
        # Then apply any mod multiplier from the original play (DT, HT, etc.)
        return round(
            hit_score * 0.96 * mods.multiplier(game_mode)
        )

def generate_unique_score_id() -> int:
    score_repo = ScoresRepository()
    return score_repo.generate_new_score_id()

def build_from_score_data(
    score_id: int,    
    score_data: ScoreData, 
    total_score_v1: int,
    total_score_v2: int,
    difficulty_adjusted_map_score: bool, 
    original_md5: str,
    pp: int
) -> Score:
    score = Score()

    score.id = score_id
    score.profile_name = score_data.username
    print(f"[BUILD_SCORE] Profile name set to: '{score.profile_name}' (from score_data.username)")
    score.beatmap.md5 = score_data.beatmap_md5
    score.beatmap.difficulty_adjusted = difficulty_adjusted_map_score
    score.beatmap.original_md5 = original_md5

    score.statistics.total_score.v1 = total_score_v1
    score.statistics.total_score.v2 = total_score_v2

    score.statistics.count_300 = score_data.count_300
    score.statistics.count_100 = score_data.count_100
    score.statistics.count_50 = score_data.count_50
    score.statistics.count_miss = score_data.count_miss
    score.statistics.combo = score_data.max_combo
    score.statistics.perfect = score_data.perfect
    score.statistics.pp = pp

    score.game_mode = GameMode.from_client(score_data.game_mode)
    score.mods = Mods.from_stable_mods(score_data.mods)

    score.replay = score_data.replay_frames

    score.epoch_time_set_at = int(score_data.play_time.timestamp())
    return score

def add(score: Score):
    scores_repo = ScoresRepository()
    submitted_score = scores_repo.add_score(score.beatmap.md5, score)
    return submitted_score

def get_map_scores_for(profile_name: str, beatmap_md5: str) -> list[Score]:
    scores_repo = ScoresRepository()
    map_scores = scores_repo.get_scores_for(profile_name, beatmap_md5)

    return map_scores

def get_all_map_scores_for_profile(profile_name: str, game_mode: GameMode) -> list[AllMapScoresForProfileResult]:
    print(f"[GET_ALL_SCORES] Retrieving scores for profile: '{profile_name}' in {game_mode}")
    scores_repo = ScoresRepository()
    return scores_repo.get_all_map_scores_for_profile(profile_name, game_mode)

def get_personal_best_for(
    profile_name: str, 
    beatmap_md5: str,
    scoring_type: ScoringType,
    game_mode: GameMode,
    with_mods: Mods | None = None,
) -> Score | None:
    scores_repo = ScoresRepository()
    map_scores = scores_repo.get_scores_for(profile_name, beatmap_md5)

    map_scores = [score for score in map_scores if score.game_mode == game_mode]

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
            return score.statistics.pp

    personal_best = max(map_scores, key=score_sort_key)
    
    return personal_best

async def _get_position_for(
    score: Score, 
    beatmap: Beatmap,
    bancho_scores: list[ossapi.models.Score],
    scoring_type: ScoringType
) -> int:
    """Internal wrapper for position calculation."""
    return await score_ranking_usecases.get_score_position(
        score=score,
        beatmap=beatmap,
        bancho_scores=bancho_scores,
        scoring_type=scoring_type,
    )

async def get_position_for(
    score: Score, 
    beatmap: Beatmap, 
    settings: ProfileSettings,
    game_mode: GameMode
) -> int:
    api_client = osu_api_usecases.get_api_client()

    legacy_only = settings.leaderboard.show_lazer_scores_on_leaderboard == False

    try:
        api_scores = await api_client.beatmap_scores(
            beatmap_id=beatmap.osu_id,
            mode=game_mode.to_api_v2(),
            legacy_only=legacy_only,
            type=settings.leaderboard.scores_sorted_by.to_api_v2(),
        )
    except ValueError:
        return 1

    return await _get_position_for(
        score=score,
        beatmap=beatmap,
        bancho_scores=api_scores.scores,
        scoring_type=settings.leaderboard.scores_sorted_by
    )