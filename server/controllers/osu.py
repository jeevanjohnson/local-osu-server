from fastapi import APIRouter, Depends, Path, Query, Response, status, Header
from typing import Literal
from core.adapters.osu_protocol.osu.leaderboard import NotSubmittedLeaderboard, UpdateBeatmapRequestLeaderboard, GraveyardLeaderboard
import server.dependencies as dependencies
from core.usecases.domain.player import Player
import orjson
from fastapi.responses import RedirectResponse
import core.usecases.domain.port as port_usecases
import core.usecases.domain.client_state as client_state_usecases
from core.models.domain.gameplay.game_mode import GameMode
from core.models.domain.gameplay.mods import Mods
import core.usecases.application.beatmaps as beatmap_usecases
import core.usecases.domain.beatmap as beatmap_domain
from core.usecases.application.beatmaps import BeatmapStatus
import core.usecases.application.leaderboards as leaderboards_usecases
from core.adapters.osu_protocol.osu.types import LeaderboardType
from core.usecases.domain.osu_api import InvalidOsuApiCredentialsError
import time
from fastapi import Request, Form, File
from fastapi.responses import RedirectResponse
import core.usecases.domain.scores as domain_scores_usecases
import core.usecases.application.scores as scores_usecases
import core.adapters.osu_protocol.osu.score_submission as score_submission_protocol

osu = APIRouter(
    prefix="/osu",
)

@osu.get("/web/osu-getseasonal.php")
async def get_seasonal_backgrounds(
    player: Player | None = Depends(dependencies.player)
):
    if player is None:
        return Response(b"[]")

    profile = player.get_profile()
    
    return Response(
        orjson.dumps(profile.seasonal_backgrounds)
    )

@osu.get("/beatmap{full_path:path}")
async def get_beatmap(
    full_path: str
):
    return RedirectResponse(
        url= f"https://osu.ppy.sh/beatmap{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY
    )

@osu.get("/users/{user_id}")
async def get_user_page(
    user_id: int = Path(...),
):
    if user_id != 2:
        response = f"https://osu.ppy.sh/users/{user_id}"
    else:
        interface_port = port_usecases.retrive_port_for("interface")

        if interface_port is None:
            response = "https://osu.ppy.sh/users/40241928046012941826421894"
        else:
            response = f"http://localhost:{interface_port}/dashboard/"
    
    return RedirectResponse(
        url=response,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )

@osu.get("/home/account/edit")
async def get_avatar_page():
    interface_port = port_usecases.retrive_port_for("interface")

    if interface_port is None:
        response = "https://osu.ppy.sh/users/40241928046012941826421894"
    else:
        response = f"http://localhost:{interface_port}/dashboard/"

    return RedirectResponse(
        url=response,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@osu.get("/web/osu-osz2-getscores.php")
async def get_leaderboard(
    requesting_from_editor_song_select: bool = Query(..., alias="s"),
    leaderboard_version: int = Query(..., alias="vv"),
    raw_leaderboard_type: int = Query(..., alias="v"),
    map_md5: str = Query(..., alias="c"),
    map_filename: str = Query(..., alias="f"),
    raw_mode_arg: int = Query(..., alias="m"),
    map_set_id: int = Query(
        ...,
        alias="i",
    ),
    raw_mods_arg: int = Query(..., alias="mods"),
    map_package_hash: str = Query(..., alias="h"),
    aqn_files_found: bool = Query(..., alias="a"),
    player: Player | None = Depends(dependencies.player)
):
    if player is None:
        client_state_usecases.restart_client()
        return Response(b"error: no")

    client_state = player.get_client_state()
    
    client_state.direct_reference.last_query = []
    client_state.direct_reference.cursor_string = None

    mode_arg = GameMode(raw_mode_arg)
    mods_arg = Mods.from_stable_int(raw_mods_arg)

    if client_state.game_mode != mode_arg:
        client_state.game_mode = mode_arg
    
    if client_state.mods != mods_arg:
        client_state.mods = mods_arg
    
    player.update_client_state(client_state)
    client_state = player.update_client_stats()

    profile = player.get_profile()

    if not profile.settings.submission.relax_submission:
        if "RX" in client_state.mods:
            player.notify("Due to your settings, scores with the RX mod will not be submitted. Please disable the RX mod to submit scores.")
    
    if not profile.settings.submission.auto_pilot_submission:
        if "AP" in client_state.mods:
            player.notify("Due to your settings, scores with the AP mod will not be submitted. Please disable the AP mod to submit scores.")

    if not profile.settings.submission.score_v2_submission:
        if "SV2" in client_state.mods:
            player.notify("Due to your settings, scores with the SV2 mod will not be submitted. Please disable the SV2 mod to submit scores.")
    
    if profile.settings.submission.force_score_v2:
        if "SV2" not in client_state.mods:
            player.notify("Due to your settings, only scores with the SV2 mod will be submitted. Please enable the SV2 mod to submit scores.")
        
    if profile.settings.submission.force_nf:
        if "NF" not in client_state.mods:
            player.notify("Due to your settings, only scores with the NF mod will be submitted. Please enable the NF mod to submit scores.")

    t0 = time.time()
    try:
        beatmap_result = await beatmap_usecases.from_leaderboard_request(
            filename=map_filename,
            md5=map_md5,
        )
    except InvalidOsuApiCredentialsError:
        client_state_usecases.restart_client()
        return Response(b"error: no")
    t1 = time.time()
    print(f"[TIMING] beatmap lookup for '{map_filename}': {(t1-t0)*1000:.2f}ms")

    beatmap = beatmap_result.beatmap
    beatmap_status = beatmap_result.status

    if beatmap_status in (BeatmapStatus.UNSUBMITTED, BeatmapStatus.NEEDS_UPDATE):
        client_state.beatmap.md5 = ""
        client_state.beatmap.id = 0
        client_state.beatmap.set_id = 0
        client_state.beatmap.is_difficulty_adjusted = False

        client_state = player.update_client_state(client_state)

        if beatmap_status == BeatmapStatus.NEEDS_UPDATE:
            leaderboard = UpdateBeatmapRequestLeaderboard()
        else:
            leaderboard = NotSubmittedLeaderboard()
        
        return Response(
            leaderboard.serialize()
        )
    
    if beatmap is None:
        return Response(b"error: no")
    
    client_state.beatmap.md5 = beatmap.md5
    client_state.beatmap.id = beatmap.osu_id
    client_state.beatmap.set_id = beatmap.osu_set_id
    client_state.beatmap.is_difficulty_adjusted = beatmap.difficulty_adjusted

    client_state = player.update_client_state(client_state)

    if player.name in beatmap.status_override:
        beatmap_status = beatmap.status_override[player.name]
    else:
        beatmap_status = beatmap.status

    if not beatmap_status.has_leaderboards():
        leaderboard = GraveyardLeaderboard()
        return Response(
            leaderboard.serialize()
        )

    leaderboard_type = LeaderboardType(raw_leaderboard_type)

    try:
        leaderboard = await leaderboards_usecases.from_client_request(
            beatmap=beatmap,
            beatmap_status=beatmap_status,
            player=player,
            leaderboard_type =leaderboard_type,
        )
    except InvalidOsuApiCredentialsError:
        client_state_usecases.restart_client()
        return Response(b"error: no")

    return Response(
        leaderboard.serialize()
    )

@osu.get("/web/maps/{map_filename}")
async def get_map_file(
    request: Request,
    map_filename: str,
    host: str = Header(...),
):
    url_path = request["raw_path"].decode().removeprefix("/osu")

    if beatmap_domain.valid_difficulty_adjusted_filename(map_filename):
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    
    return RedirectResponse(
        url=f"https://osu.ppy.sh{url_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY
    )

@osu.post("/web/osu-submit-modular-selector.php")
# log
async def osuSubmitModularSelector(
    request: Request,
    token: str = Header(...),
    exited_out: bool = Form(..., alias="x"),
    fail_time: int = Form(..., alias="ft"),
    visual_settings_b64: bytes = Form(..., alias="fs"),
    updated_beatmap_hash: str = Form(..., alias="bmk"),
    storyboard_md5: str | None = Form(None, alias="sbk"),
    iv_b64: bytes = Form(..., alias="iv"),
    unique_ids: str = Form(..., alias="c1"),
    score_time: int = Form(..., alias="st"),
    pw_md5: str = Form(..., alias="pass"),
    osu_version: str = Form(..., alias="osuver"),
    client_hash_b64: bytes = Form(..., alias="s"),
    fl_cheat_screenshot: bytes | None = File(None, alias="i"),
    player: Player | None = Depends(dependencies.player)
):
    if player is None:
        client_state_usecases.restart_client()
        return Response(b"error: no")

    score_data = score_submission_protocol.decrypt_score_submission_attempt(
        raw_score_parameters=await request.form(),
        client_hash_b64=client_hash_b64,
        iv_b64=iv_b64,
        osu_version=osu_version,
    )

    profile = player.get_profile()
    client_state = player.get_client_state()

    score_mods = Mods.from_stable_int(score_data.mods)

    if "RX" in score_mods and not profile.settings.submission.relax_submission:
        player.notify("Score submission failed: RX mod is not allowed to be submitted based on your settings.")
        return Response(b"error: no")

    if "AP" in score_mods and not profile.settings.submission.auto_pilot_submission:
        player.notify("Score submission failed: AP mod is not allowed to be submitted based on your settings.")
        return Response(b"error: no")

    if "SV2" in score_mods and not profile.settings.submission.score_v2_submission:
        player.notify("Score submission failed: SV2 mod is not allowed to be submitted based on your settings.")
        return Response(b"error: no")
    
    if "SV2" not in score_mods and profile.settings.submission.force_score_v2:
        player.notify("Score submission failed: Score V2 mod is required to be submitted based on your settings.")
        return Response(b"error: no")
    
    if "NF" not in score_mods and profile.settings.submission.force_nf:
        player.notify("Score submission failed: NF mod is required to be submitted based on your settings.")
        return Response(b"error: no")
    
    performance = player.get_performance(client_state.game_mode)

    performance.playcount += 1
    
    performance = player.update_performance(client_state.game_mode, performance)

    if not score_data.passed:
        return Response(b"ok")

    beatmap = await beatmap_usecases.get_by_md5(score_data.beatmap_md5)

    if beatmap is None:
        player.notify("Score submission failed: beatmap not found.")
        return Response(b"error: no")
    
    if player.name in beatmap.status_override:
        beatmap_status = beatmap.status_override[player.name]
    else:
        beatmap_status = await beatmap_usecases.get_current_status(beatmap)

    if "SV2" in score_mods:
        performance.total_score_v2 += score_data.total_score
    else:
        performance.total_score_v1 += score_data.total_score
    
    performance = player.update_performance(client_state.game_mode, performance)

    if not beatmap_status.has_leaderboards():
        # TODO: properly show score change on client
        return Response(score_submission_protocol.empty_charts())

    previous_personal_best = domain_scores_usecases.get_personal_best_for(
        profile_name=player.name,
        beatmap_md5=score_data.beatmap_md5,
        scoring_type=profile.settings.leaderboard.scores_sorted_by,
        game_mode=client_state.game_mode,
    )
    previous_profile = player.get_profile()

    new_score, new_profile = await scores_usecases.submit(
        score_data=score_data,
        beatmap=beatmap,
        profile_name=player.name,
        profile=player.get_profile(),
    )
    
    print(f"[OSU_SUBMIT] NEW PROFILE RETURNED:")
    print(f"[OSU_SUBMIT] - PP: {new_profile.performance[client_state.game_mode].performance_points}")
    print(f"[OSU_SUBMIT] - Rank: #{new_profile.performance[client_state.game_mode].rank}")
    print(f"[OSU_SUBMIT] - Accuracy: {new_profile.performance[client_state.game_mode].accuracy.to_percentage():.2f}%")
    
    # UPDATE PLAYER WITH NEW PROFILE
    print(f"[OSU_SUBMIT] Updating player object with new profile...")
    player.update_profile(new_profile)

    player.update_client_stats()
    
    print(f"[OSU_SUBMIT] PLAYER STATS AFTER UPDATE:")
    performance_after = player.get_performance(client_state.game_mode)
    print(f"[OSU_SUBMIT] - Player PP: {performance_after.performance_points}")
    print(f"[OSU_SUBMIT] - Player Rank: #{performance_after.rank}")

    if "RX" in score_mods or "AP" in score_mods:
        return Response(b"error: no")

    if previous_personal_best is None:
        rank_entry = score_submission_protocol.Rank(
            before=None,
            after=await domain_scores_usecases.get_position_for(
                new_score, beatmap, new_profile.settings, client_state.game_mode
            ),
        )

        if "SV2" in score_mods:
            total_score = new_score.statistics.total_score.v2
            ranked_score = new_score.statistics.total_score.v2
        else:
            ranked_score = new_score.statistics.total_score.v1
            total_score = new_score.statistics.total_score.v1

        ranked_score_entry = score_submission_protocol.RankedScore(
            before=None,
            after=ranked_score,
        )

        total_score_entry = score_submission_protocol.TotalScore(
            before=None,
            after=total_score,
        )

        max_combo_entry = score_submission_protocol.MaxCombo(
            before=None,
            after=new_score.statistics.combo,
        )

        accuracy_entry = score_submission_protocol.Accuracy(
            before=None,
            after=new_score.statistics.accuracy.to_percentage(),
        )

        pp_entry = score_submission_protocol.PerformancePoints(
            before=None,
            after=new_score.statistics.pp,
        )
    else:
        rank_entry = score_submission_protocol.Rank(
            before=await domain_scores_usecases.get_position_for(
                previous_personal_best, beatmap, new_profile.settings, client_state.game_mode
            ),
            after=await domain_scores_usecases.get_position_for(
                new_score, beatmap, new_profile.settings, client_state.game_mode
            ),
        )

        if "SV2" in score_mods:
            previous_total_score = previous_personal_best.statistics.total_score.v2
            previous_ranked_score = previous_personal_best.statistics.total_score.v2

            new_total_score = new_score.statistics.total_score.v2
            new_ranked_score = new_score.statistics.total_score.v2
        else:
            previous_ranked_score = previous_personal_best.statistics.total_score.v1
            previous_total_score = previous_personal_best.statistics.total_score.v1

            new_ranked_score = new_score.statistics.total_score.v1
            new_total_score = new_score.statistics.total_score.v1

        ranked_score_entry = score_submission_protocol.RankedScore(
            before=previous_ranked_score,
            after=new_ranked_score,
        )

        total_score_entry = score_submission_protocol.TotalScore(
            before=previous_total_score,
            after=new_total_score,
        )

        max_combo_entry = score_submission_protocol.MaxCombo(
            before=previous_personal_best.statistics.combo,
            after=new_score.statistics.combo,
        )

        accuracy_entry = score_submission_protocol.Accuracy(
            before=previous_personal_best.statistics.accuracy.to_percentage(),
            after=new_score.statistics.accuracy.to_percentage(),
        )

        pp_entry = score_submission_protocol.PerformancePoints(
            before=previous_personal_best.statistics.pp,
            after=new_score.statistics.pp,
        )

    beatmap_chart = score_submission_protocol.BeatmapChart(
        rank=rank_entry,
        ranked_score=ranked_score_entry,
        total_score=total_score_entry,
        max_combo=max_combo_entry,
        accuracy=accuracy_entry,
        pp=pp_entry,
    )

    previous_performance = previous_profile.performance[client_state.game_mode]
    new_performance = new_profile.performance[client_state.game_mode]

    rank_entry = score_submission_protocol.Rank(
        before=previous_performance.rank,
        after=new_performance.rank,
    )

    if "SV2" in score_mods:
        previous_total_score = previous_performance.total_score_v2
        previous_ranked_score = previous_performance.ranked_score_v2

        new_total_score = new_performance.total_score_v2
        new_ranked_score = new_performance.ranked_score_v2
    else:
        previous_ranked_score = previous_performance.ranked_score_v1
        previous_total_score = previous_performance.total_score_v1

        new_ranked_score = new_performance.ranked_score_v1
        new_total_score = new_performance.total_score_v1

    ranked_score_entry = score_submission_protocol.RankedScore(
        before=previous_ranked_score,
        after=new_ranked_score,
    )

    total_score_entry = score_submission_protocol.TotalScore(
        before=previous_total_score,
        after=new_total_score,
    )

    max_combo_entry = score_submission_protocol.MaxCombo(
        before=previous_performance.max_combo,
        after=new_performance.max_combo,
    )

    accuracy_entry = score_submission_protocol.Accuracy(
        before=previous_performance.accuracy.to_percentage(),
        after=new_performance.accuracy.to_percentage(),
    )

    pp_entry = score_submission_protocol.PerformancePoints(
        before=previous_performance.performance_points,
        after=new_performance.performance_points,
    )

    overall_ranking_chart = score_submission_protocol.OverallRankingChart(
        rank=rank_entry,
        ranked_score=ranked_score_entry,
        total_score=total_score_entry,
        max_combo=max_combo_entry,
        accuracy=accuracy_entry,
        pp=pp_entry,
    )

    submission_charts = score_submission_protocol.SubmissionCharts(
        beatmap_id=beatmap.osu_id,
        beatmap_set_id=beatmap.osu_set_id,
        beatmap_playcount=beatmap.play_count,
        beatmap_passcount=beatmap.pass_count,
        last_updated=beatmap.last_updated,
        score_id=new_score.id,
        achievements=score_submission_protocol.Achievements(), # TODO: Achievements?
        beatmap_chart=beatmap_chart,
        overall_ranking_chart=overall_ranking_chart,
    )

    return Response(
        submission_charts.serialize()
    )

