import json
import urllib.parse as urlparse

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse

import usecases.bancho_scores
import usecases.beatmaps
import usecases.profiles
import usecases.score_submission
import usecases.scores
import usecases.sessions
from adapters.app_logger import app_logger
from constants import SEASONAL_BG_GIT_URL
from controllers.dependencies import OsuErrors, retrieve_profile, retrieve_server_settings, retrieve_session
from models.database.profiles import CurrentProfile as Profile
from models.database.sessions import (
    CurrentSession as Session,
)
from models.database.server_settings import CurrentServerSettings as ServerSettings 
from models.database.sessions import CurrentSessionBeatmapInfo as SessionBeatmapInfo
from models.domain.gameplay import osuGameMode, osuMods
import usecases.server_settings
from osuProtocol.client_web import (
    GRAVEYARD_LEADERBOARD,
    NOT_SUBMITTED_LEADERBOARD,
    UPDATE_BEATMAP_REQUEST_LEADERBOARD,
    Leaderboard,
    LeaderboardHeader,
    LeaderboardScore,
    LeaderboardType,
    ScoringAlgorithm,
    Achievements,
    SubmissionCharts,
    UNRANKED_CHARTS
)
from usecases.providers import ApiV2CredentialsError, OsuDailyCredentialsError
from datetime import datetime

osu = APIRouter(
    prefix="/osu",
)


# osu is weird for this
@osu.get("/web/osu-getseasonal.php")
@app_logger.log(msg="router osu get seasonal backgrounds")
async def get_seasonal_backgrounds():
    return Response(content=json.dumps([SEASONAL_BG_GIT_URL]))


@osu.get("/beatmaps/{full_path:path}")
@app_logger.log(msg="router osu get beatmap redirect")
async def get_beatmap(full_path: str):
    return RedirectResponse(
        url=f"https://osu.ppy.sh/beatmaps/{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.get("/web/osu-osz2-getscores.php")
@app_logger.log(msg="router osu get leaderboard")
async def get_leaderboard(
    requesting_from_editor_song_select: bool = Query(..., alias="s"),
    leaderboard_version: int = Query(..., alias="vv"),
    leaderboard_type: int = Query(..., alias="v"),
    map_md5: str = Query(..., alias="c"),
    map_filename: str = Query(..., alias="f"),
    mode_arg: int = Query(..., alias="m"),
    map_set_id: int = Query(
        ...,
        alias="i",
    ),
    mods_arg: int = Query(..., alias="mods"),
    map_package_hash: str = Query(..., alias="h"),
    aqn_files_found: bool = Query(..., alias="a"),
    profile: Profile = Depends(retrieve_profile(OsuErrors.NON)),
    session: Session = Depends(retrieve_session(OsuErrors.NON)),
):
    map_filename = urlparse.unquote(map_filename)

    if session.songs_folder is None:
        await usecases.sessions.silent_restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    leaderboard_type = LeaderboardType(leaderboard_type)
    mode_arg = osuGameMode(mode_arg)

    if session.current_game_mode != mode_arg:
        session.current_game_mode = mode_arg

        await usecases.sessions.update_current_session(session, update_client=True)

    try:
        beatmap = await usecases.beatmaps.from_leaderboard_request(
            beatmap_md5=map_md5,
            beatmap_set_id=map_set_id,
            map_filename=map_filename,
            songs_folder=session.songs_folder,
            current_settings=profile.settings,
        )
    except ApiV2CredentialsError:
        await usecases.sessions.silent_restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    if beatmap is None:
        if not profile.settings.ignore_beatmap_updates:
            session.latest_beatmap = None
            await usecases.sessions.update_current_session(session)
            return Response(UPDATE_BEATMAP_REQUEST_LEADERBOARD)
        else:
            session.latest_beatmap = None
            await usecases.sessions.update_current_session(session)
            return Response(GRAVEYARD_LEADERBOARD)

    if beatmap.id == 0:
        # practice/unsubmitted map, just return empty leaderboard but save the beatmap info in the session so it can be used for score submission
        session.latest_beatmap = None
        await usecases.sessions.update_current_session(session)
        return Response(NOT_SUBMITTED_LEADERBOARD)

    session.latest_beatmap = SessionBeatmapInfo(
        id=beatmap.id,
        md5=beatmap.md5,
        set_id=beatmap.set_id,
    )

    await usecases.sessions.update_current_session(session)

    if not beatmap.status.has_leaderboard():
        return Response(GRAVEYARD_LEADERBOARD)

    mods = osuMods(mods_arg)

    if profile.settings.leaderboard.show_lazer_scores_on_leaderboard:
        stable_only = False
    else:
        stable_only = True

    scores = await usecases.bancho_scores.get_scores_for(
        beatmap=beatmap,
        leaderboard_type=leaderboard_type,
        game_mode=mode_arg,
        mods=mods,
        limit=profile.settings.leaderboard.leaderboard_score_limit,
        stable_only=stable_only,
    )

    # TODO: handle map updates

    total_scores = scores.total if scores else 0

    leaderboard_header = LeaderboardHeader(
        beatmap_status=beatmap.status,
        beatmap_id=beatmap.id,
        beatmap_set_id=beatmap.set_id,
        num_of_scores=total_scores,
        artist=beatmap.artist,
        title=beatmap.title,
    )

    leaderboard = Leaderboard(header=leaderboard_header, scores=[])

    if not scores:
        return Response(content=leaderboard.serialize())

    leaderboard_scores = []
    scores.sort(profile.settings.scoring_algorithm)
    scores.limit = profile.settings.leaderboard.leaderboard_score_limit

    for index, score in enumerate(scores.scores):
        if profile.settings.scoring_algorithm == ScoringAlgorithm.PP:
            ingame_score = score.performance_points or 0
        else:
            ingame_score = score.total_score

        leaderboard_score = LeaderboardScore.from_score(
            score=score,
            position=index + 1,
            ingame_score=ingame_score,
            from_difficulty_adjusted=beatmap.difficulty_adjusted,
            truncate_username=profile.settings.leaderboard.truncate_user_names_on_leaderboard,
        )
        leaderboard_scores.append(leaderboard_score)

    leaderboard.scores = leaderboard_scores

    return Response(content=leaderboard.serialize())


@osu.get("/web/maps/{map_filename}")
@app_logger.log(msg="router osu get map file")
async def get_map_file(
    request: Request,
    map_filename: str,
    host: str = Header(...),
    profile: Profile = Depends(retrieve_profile(status_code=status.HTTP_404_NOT_FOUND)),
    session: Session = Depends(retrieve_session(status_code=status.HTTP_404_NOT_FOUND)),
):
    raw_path: str = request["raw_path"].decode()
    raw_path = raw_path.removeprefix("/osu")

    if usecases.beatmaps.valid_difficulty_adjusted_beatmap_filename(map_filename):
        return Response(b"", status_code=status.HTTP_404_NOT_FOUND)

    return RedirectResponse(
        url=f"https://osu.ppy.sh{raw_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.post("/web/osu-submit-modular-selector.php")
@app_logger.log(msg="router osu submit modular selector")
async def osuSubmitModularSelector(
    request: Request,
    # TODO: should token be allowed
    # through but ac'd if not found?
    # TODO: validate token format
    # TODO: save token in the database
    token: str = Header(...),
    # TODO: do ft & st contain pauses?
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
    profile: Profile = Depends(retrieve_profile(OsuErrors.NON)),
    session: Session = Depends(retrieve_session(OsuErrors.NON)),
    server_settings: ServerSettings = Depends(retrieve_server_settings),
):
    if session.songs_folder is None:
        await usecases.sessions.silent_restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    if not await usecases.server_settings.credentials_exist():
        await usecases.sessions.restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    try:
        score_parameters = usecases.score_submission.parse_form_data(
            await request.form(),
        )

        if score_parameters is None:
            raise ValueError("Invalid score form data")

        score_data_b64, replay_file = score_parameters

        score_data, client_hash_decoded = usecases.score_submission.decrypt_score_aes_data(
            score_data_b64=score_data_b64,
            client_hash_b64=client_hash_b64,
            iv_b64=iv_b64,
            osu_version=osu_version,
        )
    except Exception as error:
        app_logger.warning(f"Failed to parse submitted score payload: {error}")
        await usecases.sessions.notify_client(
            "Failed to parse submitted score. Please try again."
        )
        return Response(OsuErrors.NON.value.encode())

    if score_data.username.lower() != session.profile_name.lower():
        print(f"Score submission profile mismatch: score submitted for {score_data.username} but current session profile is {session.profile_name}")
        await usecases.sessions.notify_client(
            "Submitted score profile mismatch. Please relog and try again."
        )
        return Response(OsuErrors.NON.value.encode())

    if not profile.settings.relax_submission and "RX" in score_data.mods:
        await usecases.sessions.notify_client(
            "Relax mod score submissions are not allowed on this server. Please disable relax and try again."
        )
        return Response(OsuErrors.NON.value.encode())

    if not score_data.passed:
        return Response(OsuErrors.NON.value.encode())

    beatmap = await usecases.beatmaps.from_score_submission_request(
        beatmap_md5=score_data.beatmap_md5,
        songs_folder=session.songs_folder,
        current_settings=profile.settings,
    )

    if beatmap is None:
        await usecases.sessions.notify_client(
            "Failed to find beatmap for submitted score. Score may not have been saved, please relog and try again."
        )
        return Response(
            OsuErrors.BEATMAP.value.encode(),
        )
    
    if not beatmap.status.has_leaderboard():
        return Response(UNRANKED_CHARTS.serialize())

    try:
        osu_file = await usecases.beatmaps.require_osu_file_for_beatmap(
            beatmap=beatmap,
            songs_folder=session.songs_folder,
        )
    except FileNotFoundError:
        await usecases.sessions.notify_client(
            "Failed to find .osu file for beatmap. Score may not have been saved, please relog and try again."
        )
        return Response(
            OsuErrors.BEATMAP.value.encode(),
        )

    score = await usecases.score_submission.submit_score(
        score_id=await usecases.scores.generate_score_id(),
        map_file=osu_file,
        score_data=score_data,
        replay_frames=await replay_file.read(),
        beatmap_max_combo=beatmap.max_combo,
        beatmap_md5=beatmap.md5,
        calc_pp=beatmap.status.ranked()
    )

    try:
        current_profile = await usecases.profiles.recalculate_stats(
            session.profile_name,
            max_combo=score.combo,
            game_mode=score.game_mode,
            server_settings=server_settings,
            scoring_algorithm=profile.settings.scoring_algorithm
        )
    except OsuDailyCredentialsError:
        await usecases.sessions.silent_restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )
    
    # TODO: Support AP?
    if "RX" in score.enabled_mods:
        return Response(OsuErrors.NON.value.encode())

    beatmap_ranking_chart, overall_ranking_chart = await usecases.scores.get_ranking_charts(
        beatmap=beatmap,
        old_profile=profile,
        current_profile=current_profile,
        new_score=score,
        settings=profile.settings
    )

    # TODO: Port bancho achievements here!
    # For now a test one for ya
    unlocked_achievements = Achievements()

    # unlocked_achievements.append(
    #     Achievement(
    #         image_url="https://cdn.discordapp.com/attachments/737236214062645338/908465184425795614/unknown.png?ex=69c104e2&is=69bfb362&hm=21fbd56213faf386632c0a9b9ce2d3a989c4e1220bda3f35f098f69ad71d4d46&",
    #         title="Test Achievement",
    #         description="This is a test achievement. Congrats on unlocking it!",
    #     )
    # )

    submission_charts = SubmissionCharts(
        beatmap_id=beatmap.id,
        beatmap_set_id=beatmap.set_id,
        beatmap_playcount=1, # TODO: Get this
        beatmap_passcount=1, # TODO: Get this
        last_update=datetime.now(), # TODO: Get this
        score_id=score.id,
        achievements=unlocked_achievements,
        beatmap_chart=beatmap_ranking_chart,
        overall_ranking_chart=overall_ranking_chart,
    )

    await usecases.sessions.update_current_session(
        session,
        update_client=True,
    )

    return Response(content=submission_charts.serialize())

    
    


    

