from core.models.database.beatmaps import Beatmap
from core.usecases.domain.player import Player
from core.osu_protocol.osu.types import LeaderboardType
from core.osu_protocol.osu.leaderboard import Leaderboard, LeaderboardHeader, LeaderboardScore
import core.usecases.domain.scores as scores_usecases
import core.usecases.domain.osu_api as osu_api_usecases
from core.models.domain.gameplay.rank_status import RankStatus
from core.models.domain.gameplay.mods import Mods
from core.models.database.scores import Score
import core.usecases.application.bancho.scores as bancho_scores_usecases
from core.usecases.application.bancho.scores import BanchoScore
from core.models.domain.gameplay.scoring import ScoringType
from core.usecases.adapters.score import ScoreEstimator, ScoreDataPoint, ScoringVersion
import core.usecases.domain.calculator.position as score_position_calculator_usecases
import core.usecases.application.beatmaps as beatmap_usecases

def bancho_score_to_leaderboard_score(
    score: BanchoScore, 
    position: int, 
    total_score: int,
    difficulty_adjusted: bool
) -> LeaderboardScore:
    if difficulty_adjusted:
        if score.lazer:
            mod_str = ",".join(
                score.mods.to_lazer_specific_mods(ignore=["CL"], include_rate=True)
            )
            title = f"(lazer) {score.username} ({mod_str})"
        else:
            rate_result = score.mods.rate()
            title = f"{score.username} ({rate_result['rate']}X)"
    else:
        if score.lazer:
            mod_str = ",".join(score.mods.to_lazer_specific_mods(ignore=["CL"]))
            
            title = f"(lazer) {score.username}"            
        
            if mod_str:
                title += f" ({mod_str})"
        else:
            title = score.username

    replay_available = (
        score.replay_available
        and not score.lazer # stable score
        and not difficulty_adjusted # not difficulty adjusted
    )

    if difficulty_adjusted or score.mods.custom_rate():
        stable_mods = score.mods.to_stable_mods(remove_rate_mods=True)
    else:
        stable_mods = score.mods.to_stable_mods()

    return LeaderboardScore(
        score_id = -score.score_id,
        username = title,
        score = total_score,
        max_combo = score.combo,
        count50 = score.count50,
        count100 = score.count100,
        count300 = score.count300,
        count_miss = score.count_miss,
        countkatu = 0,
        countgeki = 0,
        perfect = score.perfect,
        enabled_mods = stable_mods,
        user_id = score.user_id,
        position = position,
        time_set_epoch = score.time_set,
        replay_available = replay_available,
    )

def score_to_leaderboard_score(score: Score, position: int) -> LeaderboardScore:
    return LeaderboardScore(
        score_id = score.id,
        username = score.profile_name,
        score = score.statistics.score,
        max_combo = score.statistics.combo,
        count50 = score.statistics.count_50,
        count100 = score.statistics.count_100,
        count300 = score.statistics.count_300,
        count_miss = score.statistics.count_miss,
        countkatu = 0,
        countgeki = 0,
        perfect = score.statistics.perfect,
        enabled_mods = score.mods.to_stable_mods(),
        user_id = 2,
        position = position,
        time_set_epoch = score.epoch_time_set_at,
        replay_available = True if score.replay else False,
    )

def only_one_or_less_score_on_leaderboard(
    beatmap: Beatmap, 
    beatmap_status: RankStatus, 
    score: Score | None = None
) -> Leaderboard:
    leaderboard_header = LeaderboardHeader(
        beatmap_status = beatmap_status.to_client(),
        beatmap_id = beatmap.osu_id,
        beatmap_set_id = beatmap.osu_set_id,
        num_of_scores = 0,
        artist = beatmap.artist,
        title = beatmap.title
    )

    if score is None:
        return Leaderboard(
            header=leaderboard_header,
            scores=[],
            personal_best=None,
        )

    leaderboard_header.num_of_scores = 1
    personal_best_leaderboard_score = score_to_leaderboard_score(score, position=1)

    return Leaderboard(
        header=leaderboard_header,
        scores=[personal_best_leaderboard_score],
        personal_best=personal_best_leaderboard_score,
    )

async def global_leaderboard(
    beatmap: Beatmap,
    beatmap_status: RankStatus,
    player: Player,
) -> Leaderboard:
    """Generate a global leaderboard response based on the client request."""
    personal_best = scores_usecases.get_personal_best_for(player.name, beatmap.md5)

    api_client = osu_api_usecases.get_api_client()

    client_state = player.get_client_state()
    profile = player.get_profile()

    try:
        legacy_only = profile.settings.leaderboard.show_lazer_scores_on_leaderboard == False

        api_scores = await api_client.beatmap_scores(
            beatmap_id=beatmap.osu_id,
            mode=client_state.game_mode.to_api_v2(),
            legacy_only=legacy_only,
            type=profile.settings.leaderboard.scores_sorted_by.to_api_v2(),
        )
    except ValueError:
        return only_one_or_less_score_on_leaderboard(beatmap, beatmap_status, personal_best)

    if not api_scores:
        return only_one_or_less_score_on_leaderboard(beatmap, beatmap_status, personal_best)
    
    if profile.settings.leaderboard.scores_sorted_by == ScoringType.SCOREV1:
        training_data: list[ScoreDataPoint] = []
        for api_score in api_scores.scores:
            if not api_score.legacy_total_score:
                continue

            # Get the mod multiplier used for this score
            mods = Mods.from_api_v2(api_score.mods)
            mod_mult = mods.mod_multipler(client_state.game_mode)
            
            training_data.append(ScoreDataPoint(
                count_300=api_score.statistics.great or 0,
                count_100=api_score.statistics.ok or 0,
                count_50=api_score.statistics.meh or 0,
                count_miss=api_score.statistics.miss or 0,
                combo=api_score.max_combo,
                score=api_score.legacy_total_score,
                mod_multiplier=mod_mult
            ))
        
        score_estimator = ScoreEstimator(version=ScoringVersion.V1)
        score_estimator.train(training_data)
    else:
        score_estimator = ScoreEstimator(version=ScoringVersion.V2)
    
    scores: list[BanchoScore | Score] = [
        bancho_scores_usecases.from_api_to_bancho_score(score, client_state.game_mode) 
        for score in api_scores.scores
    ]

    if personal_best:
        scores.append(personal_best)

    def sort_key(score: BanchoScore | Score) -> int:
        if profile.settings.leaderboard.scores_sorted_by == ScoringType.PP:
            return score.pp
        
        if isinstance(score, BanchoScore):
            mod_mult = score.mods.mod_multipler(score.game_mode)

            if score.score_override is not None:
                return score.score_override

            if profile.settings.leaderboard.scores_sorted_by == ScoringType.SCOREV1:
                return score_estimator.estimate(
                    count_300=score.count300,
                    count_100=score.count100,
                    count_50=score.count50,
                    count_miss=score.count_miss,
                    combo=score.combo,
                    mod_multiplier=mod_mult
                )
            else:
                return score_estimator.estimate(
                    count_300=score.count300,
                    count_100=score.count100,
                    count_50=score.count50,
                    count_miss=score.count_miss,
                    combo=score.combo,
                    beatmap_max_combo=beatmap.max_combo,
                    mod_multiplier=mod_mult
                )
        
        return score.statistics.score
    
    scores.sort(key=sort_key, reverse=True)

    top_scores = scores[:profile.settings.leaderboard.score_limit]

    leaderboard_scores: list[LeaderboardScore] = []

    for index, score in enumerate(top_scores):
        if not isinstance(score, BanchoScore):
            leaderboard_scores.append(score_to_leaderboard_score(score, position=index+1))
            continue
        
        if profile.settings.leaderboard.scores_sorted_by == ScoringType.PP:
            total_score = score.pp
        elif score.score_override is not None:
            total_score = score.score_override
        else:
            print(f"[LEADERBOARD DEBUG] Processing score for user {score.username}")
            kwargs = {
                "count_300": score.count300,
                "count_100": score.count100,
                "count_50": score.count50,
                "count_miss": score.count_miss,
                "combo": score.combo,
                "mod_multiplier": score.mods.mod_multipler(score.game_mode)
            }
            
            if profile.settings.leaderboard.scores_sorted_by == ScoringType.SCOREV1:
                total_score = score_estimator.estimate(**kwargs)
            else:
                kwargs["beatmap_max_combo"] = beatmap.max_combo
                total_score = score_estimator.estimate(**kwargs)
            
            print(f"[LEADERBOARD DEBUG] Estimated score for {score.username}: {total_score} (based on {kwargs})")

        leaderboard_scores.append(
            bancho_score_to_leaderboard_score(
                score, 
                position=index+1, 
                total_score=total_score,
                difficulty_adjusted=beatmap.difficulty_adjusted
            )
        )

    if beatmap.status.has_leaderboards():
        total_scores = await beatmap_usecases.get_pass_count(beatmap)
    else:
        total_scores = len(
            scores_usecases.get_map_scores_for(player.name, beatmap.md5)
        )

    leaderboard_header = LeaderboardHeader(
        beatmap_status = beatmap_status.to_client(),
        beatmap_id = beatmap.osu_id,
        beatmap_set_id = beatmap.osu_set_id,
        num_of_scores = total_scores,
        artist = beatmap.artist,
        title = beatmap.title
    )

    if personal_best:
        if personal_best in top_scores:
            personal_best_position = top_scores.index(personal_best) + 1
        else:
            personal_best_position = score_position_calculator_usecases.get_leaderboard_position(
                sorting_value=personal_best.statistics.score,
                leaderboard_scores=[
                    (idx + 1, score.score) for idx, score in enumerate(leaderboard_scores)
                ],
                total_scores=total_scores
            )
    
        return Leaderboard(
            header=leaderboard_header,
            scores=leaderboard_scores,
            personal_best=score_to_leaderboard_score(personal_best, position=personal_best_position)
        )

    return Leaderboard(
        header=leaderboard_header,
        scores=leaderboard_scores,
        personal_best=None
    )

async def from_client_request(
    beatmap: Beatmap,
    beatmap_status: RankStatus,
    player: Player,
    leaderboard_type: LeaderboardType
) -> Leaderboard:
    """Generate a leaderboard response based on the client request."""
    if leaderboard_type == LeaderboardType.TOP:
        return await global_leaderboard(beatmap, beatmap_status, player)
    elif leaderboard_type == LeaderboardType.FRIENDS:
        ...
    elif leaderboard_type == LeaderboardType.MODS:
        ...
    elif leaderboard_type == LeaderboardType.COUNTRY:
        ...