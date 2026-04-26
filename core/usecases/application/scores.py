
from core.models.domain.normalizers import Accuracy
from core.osu_protocol.osu.score_submission import ScoreData
from core.models.database.beatmaps import Beatmap
from core.models.database.scores import Score
import core.usecases.domain.scores as scores_usecases
from core.osu_protocol.domain.enums import osuMods
from core.models.domain.gameplay.mods import Mods
from core.models.domain.gameplay.game_mode import GameMode
import core.usecases.domain.calculator.pp as performance_calculator
import core.usecases.domain.calculator.rank as rank_calculator
import core.usecases.domain.beatmap as beatmaps_usecases
from core.models.adapters.database.profile import Profile
import core.usecases.domain.profiles as profiles_usecases

def recalculate_profile(
    profile_name: str, 
    profile: Profile, 
    game_mode: GameMode,
    max_combo: int | None = None,
) -> Profile:
    print(f"[RECALC_PROFILE] Starting profile recalculation for {profile_name} in {game_mode}")
    scores = scores_usecases.get_all_map_scores_for_profile(profile_name, game_mode)
    print(f"[RECALC_PROFILE] Retrieved scores: {len(scores)} maps")
    performance = profile.performance[game_mode]

    best_scores_per_map: list[Score] = []
    ranked_score_v1 = 0
    ranked_score_v2 = 0

    for map_scores_result in scores:
        md5 = map_scores_result["beatmap_md5"]
        map_scores = map_scores_result["scores"]

        if not map_scores:
            continue

        for score in map_scores:
            ranked_score_v1 += score.statistics.total_score.v1
            ranked_score_v2 += score.statistics.total_score.v2
            

        best_score_for_map = max(
            map_scores,
            key=lambda s: (
                s.statistics.pp, 
                s.statistics.total_score.v1, 
                s.statistics.total_score.v2, 
                s.epoch_time_set_at
            ),
        )

        best_scores_per_map.append(best_score_for_map)
    
    print(f"[RECALC_PROFILE] Found {len(best_scores_per_map)} best scores per map")
    # Weighting for pp/acc is based on best plays only.
    pp_source_scores = best_scores_per_map.copy()

    pp_source_scores.sort(
        key=lambda score: score.statistics.pp,
        reverse=True,
    )

    score_count = len(pp_source_scores)
    print(f"[RECALC_PROFILE] Total unique maps played: {score_count}")
    
    if score_count:
        top_scores = pp_source_scores[:100]
        weights = [0.95**i for i, _ in enumerate(top_scores)]
        
        print(f"[RECALC_PROFILE] Top 100 scores: {[f'{s.statistics.pp}pp' for s in top_scores]}")

        weighted_pp = sum(
            score.statistics.pp * weight
            for score, weight in zip(top_scores, weights)
        )
        weighted_acc = sum(
            score.statistics.accuracy * weight for score, weight in zip(top_scores, weights)
        )
        weight_total = sum(weights)

        computed_accuracy = weighted_acc / weight_total if weight_total else 0.0
        performance.accuracy = Accuracy(computed_accuracy)
        print(f"[RECALC_PROFILE] Weighted PP: {weighted_pp}, Computed Accuracy: {computed_accuracy}")
    else:
        weighted_pp = 0.0
        performance.accuracy = Accuracy(0.0)
        print(f"[RECALC_PROFILE] No scores found for profile")

    performance.ranked_score_v1 = ranked_score_v1
    performance.ranked_score_v2 = ranked_score_v2

    bonus_pp = 416.6667 * (1 - 0.9994**score_count) if score_count else 0.0
    final_pp = round(weighted_pp + bonus_pp)
    print(f"[RECALC_PROFILE] Bonus PP: {bonus_pp}, Final PP: {final_pp}")
    performance.performance_points = final_pp

    if max_combo is not None:
        if max_combo > performance.max_combo:
            performance.max_combo = max_combo

    print(f"[RECALC_PROFILE] Calculating rank for {performance.performance_points}pp")
    performance.rank = rank_calculator.calculate_rank_for(
        performance.performance_points, 
        game_mode
    )
    print(f"[RECALC_PROFILE] Calculated rank: #{performance.rank}")

    profile.performance[game_mode] = performance
    print(f"[RECALC_PROFILE] Profile recalculation complete - PP: {performance.performance_points}, Rank: {performance.rank}")

    return profiles_usecases.update_profile(profile_name, profile)


async def submit(
    score_data: ScoreData,
    beatmap: Beatmap,
    profile_name: str,
    profile: Profile,
) -> tuple[Score, Profile]:
    print(f"[SCORE_SUBMIT] Starting score submission for {profile_name}")
    print(f"[SCORE_SUBMIT] Beatmap: {beatmap.md5}, Mods: {score_data.mods}, Combo: {score_data.max_combo}")
    print(f"[SCORE_SUBMIT] Hits: 300={score_data.count_300}, 100={score_data.count_100}, 50={score_data.count_50}, Miss={score_data.count_miss}")
    
    osu_file = beatmaps_usecases.get_path_by_md5(beatmap.md5)
    assert osu_file, "Beatmap file must be available for score submission"
    print(f"[SCORE_SUBMIT] OSU file path: {osu_file}")

    if osuMods.SCOREV2 & score_data.mods:
        total_score_v1 = await scores_usecases.calculate_total_score_v1(
            beatmap=beatmap,
            count300=score_data.count_300,
            count100=score_data.count_100,
            count50=score_data.count_50,
            count_miss=score_data.count_miss,
            combo=score_data.max_combo,
            mods=Mods.from_stable_mods(score_data.mods),
            game_mode=GameMode.from_client(score_data.game_mode),
        )
        total_score_v2 = score_data.total_score
    else:
        total_score_v1 = score_data.total_score
        total_score_v2 = scores_usecases.calculate_total_score_v2(
            count300=score_data.count_300,
            count100=score_data.count_100,
            count50=score_data.count_50,
            count_miss=score_data.count_miss,
            combo=score_data.max_combo,
            beamtap_max_combo=beatmap.max_combo,
            mods=Mods.from_stable_mods(score_data.mods),
            game_mode=GameMode.from_client(score_data.game_mode),
        )

    calculated_pp = performance_calculator.calculate(
        map_file=osu_file,
        game_mode=GameMode.from_client(score_data.game_mode),
        mods=Mods.from_stable_mods(score_data.mods),
        combo=score_data.max_combo,
        n300=score_data.count_300,
        n100=score_data.count_100,
        n50=score_data.count_50,
        nmiss=score_data.count_miss,
    )
    print(f"[SCORE_SUBMIT] Calculated PP: {calculated_pp}")
    
    score = scores_usecases.build_from_score_data(
        score_id=scores_usecases.generate_unique_score_id(),
        score_data=score_data,
        total_score_v1=total_score_v1,
        total_score_v2=total_score_v2,
        difficulty_adjusted_map_score=beatmap.difficulty_adjusted,
        original_md5=beatmap.original_beatmap_md5,
        pp=calculated_pp,
    )
    print(f"[SCORE_SUBMIT] Score object created with PP: {score.statistics.pp}")

    submitted_score = scores_usecases.add(score)
    print(f"[SCORE_SUBMIT] Score saved to database")

    # recalc profile
    print(f"[SCORE_SUBMIT] Starting profile recalculation...")
    profile = recalculate_profile(
        profile_name, 
        profile, 
        GameMode.from_client(score_data.game_mode),
        max_combo=score_data.max_combo,
    )
    print(f"[SCORE_SUBMIT] Profile recalculation complete - Final PP: {profile.performance[GameMode.from_client(score_data.game_mode)].performance_points}")

    return submitted_score, profile