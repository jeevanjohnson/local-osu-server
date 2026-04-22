from core.models.database.beatmaps import Beatmap
from core.usecases.domain.player import Player
from core.osu_protocol.osu.types import LeaderboardType
from core.osu_protocol.osu.leaderboard import Leaderboard, LeaderboardHeader, LeaderboardScore
import core.usecases.domain.scores as scores_usecases
import asyncio
import core.usecases.domain.osu_api as osu_api_usecases
import core.usecases.application.score_ranking as score_ranking_usecases
from core.models.domain.gameplay.rank_status import RankStatus
from core.models.domain.gameplay.mods import Mods
from core.models.database.scores import Score
import core.usecases.application.bancho.scores as bancho_scores_usecases
from core.usecases.application.bancho.scores import BanchoScore
from core.models.domain.gameplay.scoring import ScoringType
import core.usecases.application.beatmaps as beatmap_usecases
import core.usecases.domain.beatmap as domain_beatmap_usecases

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

def score_to_leaderboard_score(score: Score, position: int, scoring_type: ScoringType) -> LeaderboardScore:
    if scoring_type == ScoringType.SCOREV1:
        total_score = score.statistics.total_score.v1
    else:
        total_score = score.statistics.total_score.v2

    return LeaderboardScore(
        score_id = score.id,
        username = score.profile_name,
        score = total_score,
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
    scoring_type: ScoringType,
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
    personal_best_leaderboard_score = score_to_leaderboard_score(
        score, position=1, scoring_type=scoring_type
    )

    return Leaderboard(
        header=leaderboard_header,
        scores=[personal_best_leaderboard_score],
        personal_best=personal_best_leaderboard_score,
    )

async def build_leaderboard_from_scores(
    scores: list[BanchoScore | Score],
    beatmap: Beatmap,
    beatmap_status: RankStatus,
    player: Player,
    personal_best: Score | None,
    personal_best_position: int | None = None,
):
    if personal_best and personal_best not in scores:
        scores.append(personal_best)

    profile = player.get_profile()

    def sort_key(score: BanchoScore | Score) -> int:
        if profile.settings.leaderboard.scores_sorted_by == ScoringType.PP:
            if isinstance(score, Score):
                return score.statistics.pp
            
            return score.pp
        
        if isinstance(score, BanchoScore):
            return score.total_score
        
        if profile.settings.leaderboard.scores_sorted_by == ScoringType.SCOREV1:
            return score.statistics.total_score.v1
        else:
            return score.statistics.total_score.v2
    
    scores.sort(key=sort_key, reverse=True)

    top_scores = scores[:profile.settings.leaderboard.score_limit]

    leaderboard_scores: list[LeaderboardScore] = []

    for index, score in enumerate(top_scores):
        if not isinstance(score, BanchoScore):
            leaderboard_scores.append(
                score_to_leaderboard_score(
                    score, position=index+1, scoring_type=profile.settings.leaderboard.scores_sorted_by
                )
            )
            continue
        
        if profile.settings.leaderboard.scores_sorted_by == ScoringType.PP:
            total_score = score.pp
        else:
            total_score = score.total_score
        
        leaderboard_scores.append(
            bancho_score_to_leaderboard_score(
                score, 
                position=index+1, 
                total_score=total_score,
                difficulty_adjusted=beatmap.difficulty_adjusted
            )
        )

    if beatmap.status.has_leaderboards():
        total_scores = await domain_beatmap_usecases.get_pass_count(beatmap)
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
        if personal_best_position is None:
            # This shouldn't happen - get_score_position() should always return a valid position
            personal_best_position = 1
    
        return Leaderboard(
            header=leaderboard_header,
            scores=leaderboard_scores,
            personal_best=score_to_leaderboard_score(
                personal_best, 
                position=personal_best_position, 
                scoring_type=profile.settings.leaderboard.scores_sorted_by
            )
        )

    return Leaderboard(
        header=leaderboard_header,
        scores=leaderboard_scores,
        personal_best=None
    )

async def general_leaderboard(
    beatmap: Beatmap,
    beatmap_status: RankStatus,
    player: Player,
    selected_mods: Mods | None = None,
) -> Leaderboard:
    """Generate a global leaderboard response based on the client request."""
    profile = player.get_profile()
    client_state = player.get_client_state()

    personal_best = scores_usecases.get_personal_best_for(
        profile_name=player.name,
        beatmap_md5=beatmap.md5,
        scoring_type=profile.settings.leaderboard.scores_sorted_by,
        game_mode=client_state.game_mode,
        with_mods=selected_mods
    )

    api_client = osu_api_usecases.get_api_client()

    client_state = player.get_client_state()
    profile = player.get_profile()

    try:
        legacy_only = profile.settings.leaderboard.show_lazer_scores_on_leaderboard == False

        if selected_mods is not None:
            mods = selected_mods.to_osu_api_v2()
        else:
            mods = None

        # Fetch all scores and filtered scores in parallel
        all_api_scores_task = api_client.beatmap_scores(
            beatmap_id=beatmap.osu_id,
            mode=client_state.game_mode.to_api_v2(),
            legacy_only=legacy_only,
            type=profile.settings.leaderboard.scores_sorted_by.to_api_v2(),
            mods=None,  # No filter for position calculation
        )

        filtered_api_scores_task = api_client.beatmap_scores(
            beatmap_id=beatmap.osu_id,
            mode=client_state.game_mode.to_api_v2(),
            legacy_only=legacy_only,
            type=profile.settings.leaderboard.scores_sorted_by.to_api_v2(),
            mods=mods,
        )

        all_api_scores, api_scores = await asyncio.gather(all_api_scores_task, filtered_api_scores_task)
        
    except ValueError:
        return only_one_or_less_score_on_leaderboard(
            beatmap, beatmap_status, profile.settings.leaderboard.scores_sorted_by, personal_best
        )

    if not api_scores:
        return only_one_or_less_score_on_leaderboard(
            beatmap, beatmap_status, profile.settings.leaderboard.scores_sorted_by, personal_best
        )

    # Calculate personal best position based on ALL scores
    personal_best_position = None
    if personal_best and all_api_scores:
        personal_best_position = await score_ranking_usecases.get_score_position(
            score=personal_best,
            beatmap=beatmap,
            bancho_scores=all_api_scores.scores,
            scoring_type=profile.settings.leaderboard.scores_sorted_by,
        )

    if "SV2" in client_state.mods and profile.settings.leaderboard.show_only_lazer_scores_on_leaderboard_with_score_v2_enabled:
        api_scores.scores = [score for score in api_scores.scores if not score.legacy_score_id]
    
    scores: list[BanchoScore | Score] = [
        bancho_scores_usecases.from_api_to_bancho_score(
            score, client_state.game_mode, profile.settings.leaderboard.scores_sorted_by
        ) 
        for score in api_scores.scores
    ]

    return await build_leaderboard_from_scores(
        scores=scores,
        beatmap=beatmap,
        beatmap_status=beatmap_status,
        player=player,
        personal_best=personal_best,
        personal_best_position=personal_best_position,
    )

async def from_client_request(
    beatmap: Beatmap,
    beatmap_status: RankStatus,
    player: Player,
    leaderboard_type: LeaderboardType
) -> Leaderboard:
    """Generate a leaderboard response based on the client request."""
    if leaderboard_type == LeaderboardType.TOP:
        return await general_leaderboard(
            beatmap, 
            beatmap_status, 
            player
        )
    elif leaderboard_type == LeaderboardType.FRIENDS:
        raise NotImplementedError("Friends leaderboard not yet implemented")
    elif leaderboard_type == LeaderboardType.MODS:
        client_state = player.get_client_state()

        return await general_leaderboard(
            beatmap, 
            beatmap_status, 
            player, 
            selected_mods=client_state.mods
        )
    elif leaderboard_type == LeaderboardType.COUNTRY:
        raise NotImplementedError("Country leaderboard not yet implemented")
    else:
        raise ValueError(f"Unknown leaderboard type: {leaderboard_type}")