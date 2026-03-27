from starlette.datastructures import FormData

import usecases.application.beatmaps
import usecases.application.client.state
import usecases.application.client.update
import usecases.application.score_submission
import usecases.application.scores
import usecases.domain.achievements
import usecases.domain.osufile
import usecases.domain.profiles
import usecases.domain.score_submission
import usecases.domain.scores
from models.database.profiles import CurrentProfile as Profile
from models.domain.errors import OsuErrors
from osu_protocol.osu.charts import UNRANKED_CHARTS, SubmissionCharts
import usecases.domain.cache_control


async def process_submission(
    raw_score_parameters: FormData,
    client_hash_b64: bytes,
    iv_b64: bytes,
    osu_version: str,
    profile: Profile,
    profile_name: str,
) -> tuple[OsuErrors, int] | tuple[SubmissionCharts, int]:
    try:
        (
            score_data,
            client_hash_decoded,
            replay_file,
        ) = await usecases.domain.score_submission.decrypt(
            raw_score_parameters=raw_score_parameters,
            client_hash_b64=client_hash_b64,
            iv_b64=iv_b64,
            osu_version=osu_version,
        )
    except Exception as e:
        await usecases.application.client.update.notify(
            f"error decrypting score submission data. {e}"
        )
        return OsuErrors.NON, 0

    invalid_submission_conditions = [
        "RX" in score_data.mods and not profile.settings.submission.relax_submission,
        "AP" in score_data.mods
        and not profile.settings.submission.auto_pilot_submission,
        "SV2" in score_data.mods
        and not profile.settings.submission.score_v2_submission,
        profile.settings.submission.force_score_v2 and not "SV2" in score_data.mods,
        profile.settings.submission.force_nf and not "NF" in score_data.mods,
    ]

    if any(invalid_submission_conditions):
        await usecases.application.client.update.notify(
            "Score submission rejected due to user settings. Please adjust your submission settings in the profile to allow this score to be submitted."
        )
        return OsuErrors.NON, 0

    if not score_data.passed:  # player quit or failed map
        return OsuErrors.NON, 0

    beatmap = await usecases.application.beatmaps.from_score_submission_request(
        beatmap_md5=score_data.beatmap_md5,
        profile_name=profile_name,
    )

    if beatmap is None:
        await usecases.application.client.update.notify(
            "Failed to find beatmap for submitted score. Score may not have been saved, please relog and try again."
        )
        return OsuErrors.BEATMAP, 0

    usecases.domain.cache_control.clear_leaderboard_cache()

    # Refresh beatmap status from API to detect any status changes (e.g., PENDING → RANKED)
    bmap_status = beatmap.status[profile_name]
    if not bmap_status.permanent:
        beatmap = await usecases.application.beatmaps.refresh_status_from_api(
            profile_name=profile_name,
            beatmap=beatmap,
        )

    bmap_status = beatmap.status[profile_name]
    if not bmap_status.has_leaderboard():
        return UNRANKED_CHARTS, 0

    osu_file = await usecases.domain.osufile.for_beatmap(
        beatmap=beatmap,
    )

    if osu_file is None:
        await usecases.application.client.update.notify(
            "Failed to find .osu file for beatmap. Score may not have been saved, please relog and try again."
        )
        return OsuErrors.BEATMAP, 0

    score = await usecases.domain.score_submission.submit(
        score_id=await usecases.domain.scores.generate_score_id(),
        map_file=osu_file,
        score_data=score_data,
        replay_frames=await replay_file.read(),
        beatmap_max_combo=beatmap.max_combo,
        beatmap_md5=beatmap.md5,
        calc_pp=bmap_status.ranked(),
    )

    usecases.domain.cache_control.clear_profiles_cache()

    # Incase of any difficulty adjustment corruption
    # lets save the .osu file & audio file here so we can
    # if needed, recover the beatmap & replay
    if beatmap.difficulty_adjusted:
        await usecases.domain.osufile.store(osu_file, store_audio=True)

    current_profile = await usecases.domain.profiles.recalculate_stats(
        profile_name=profile_name,
        score_submitted_combo=score.combo,
        game_mode=score.game_mode,
    )

    if current_profile is None:
        await usecases.application.client.update.notify(
            "Failed to recalculate profile stats after score submission. Score may not have been saved, please relog and try again."
        )
        return OsuErrors.NON, 0

    # Update client state game mode to match the score's game mode BEFORE queuing stats
    await usecases.application.client.state.update_game_mode_and_mods(
        score.game_mode, score.enabled_mods
    )

    if "RX" in score.enabled_mods or "AP" in score.enabled_mods:
        await usecases.application.client.update.stats_with_profile(current_profile)
        return OsuErrors.NON, score.id

    (
        beatmap_ranking_chart,
        overall_ranking_chart,
    ) = await usecases.application.scores.get_ranking_charts(
        beatmap=beatmap,
        old_profile=profile,
        current_profile=current_profile,
        new_score=score,
        scoring_algorithm=profile.settings.scoring.algorithm,
        leaderboard_limit=profile.settings.leaderboard.score_limit,
    )

    # TODO: Port bancho achievements here!
    unlocked_achievements = await usecases.domain.achievements.get()

    submission_charts = SubmissionCharts(
        beatmap_id=beatmap.id,
        beatmap_set_id=beatmap.set_id,
        beatmap_playcount=beatmap.play_count,
        beatmap_passcount=beatmap.pass_count,
        last_updated=beatmap.last_updated,
        score_id=score.id,
        achievements=unlocked_achievements,
        beatmap_chart=beatmap_ranking_chart,
        overall_ranking_chart=overall_ranking_chart,
    )

    # ClientState is already updated above for RX/AP path, ensure it's updated here too
    await usecases.application.client.update.stats_with_profile(current_profile)

    return submission_charts, score.id
