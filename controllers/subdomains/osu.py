import json
import urllib.parse as urlparse

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Path,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse

import usecases.bancho_scores
import usecases.beatmaps
import usecases.direct
import usecases.leaderboards
import usecases.osu_files
import usecases.profiles
import usecases.replay
import usecases.score_submission
import usecases.scores
import usecases.server_settings
import usecases.sessions
import usecases.songs_folder
from adapters import log, log_time
from constants import SEASONAL_BG_GIT_URL
from controllers.dependencies import (
    OsuErrors,
    retrieve_profile,
    retrieve_server_settings,
    retrieve_session,
)
from models.database.profiles import CurrentProfile as Profile
from models.database.server_settings import CurrentServerSettings as ServerSettings
from models.database.sessions import (
    CurrentSession as Session,
)
from models.database.sessions import CurrentSessionBeatmapInfo as SessionBeatmapInfo
from models.domain.gameplay import Mods, osuGameMode
from osuProtocol.client_web import (
    GRAVEYARD_LEADERBOARD,
    NOT_SUBMITTED_LEADERBOARD,
    UNRANKED_CHARTS,
    UPDATE_BEATMAP_REQUEST_LEADERBOARD,
    Achievements,
    LeaderboardType,
    SubmissionCharts,
    osu_direct_mode_to_osu_api_v2,
    osu_direct_ranked_status_to_osu_api_v2,
)
from usecases.providers import ApiV2CredentialsError, OsuDailyCredentialsError

osu = APIRouter(
    prefix="/osu",
)


# osu is weird for this
@osu.get("/web/osu-getseasonal.php")
@log_time
async def get_seasonal_backgrounds():
    return Response(content=json.dumps([SEASONAL_BG_GIT_URL]))


@osu.get("/beatmap{full_path:path}")
@log_time
async def get_beatmap(full_path: str):
    return RedirectResponse(
        url=f"https://osu.ppy.sh/beatmap{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.get("/web/osu-osz2-getscores.php")
@log_time
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
    # if we are on the leaderboard, make sure our direct search history is cleared since it's not relevant anymore
    session.osu_client.previous_direct_search = []
    session.osu_client.direct_cursor_string = None
    await usecases.sessions.update_current_session(session)

    mods = Mods.from_stable_mods(mods_arg)
    game_mode = osuGameMode(mode_arg)

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
        session.latest_beatmap = None
        await usecases.sessions.update_current_session(session)
        return Response(UPDATE_BEATMAP_REQUEST_LEADERBOARD)

    if beatmap.unsubmitted:
        session.latest_beatmap = None
        await usecases.sessions.update_current_session(session)
        return Response(NOT_SUBMITTED_LEADERBOARD)

    session.latest_beatmap = SessionBeatmapInfo(
        id=beatmap.id,
        md5=beatmap.md5,
        set_id=beatmap.set_id,
        is_difficulty_adjusted=beatmap.difficulty_adjusted,
    )

    await usecases.sessions.update_current_session(session)

    if not beatmap.status.has_leaderboard():
        return Response(GRAVEYARD_LEADERBOARD)

    mods = Mods.from_stable_mods(mods_arg)

    leaderboard = await usecases.leaderboards.from_request(
        beatmap=beatmap,
        leaderboard_type=leaderboard_type,
        game_mode=game_mode,
        mods=mods,
        profile_name=session.profile_name,
        settings=profile.settings,
        profile=profile,
    )
    return Response(content=leaderboard.serialize())


@osu.get("/web/maps/{map_filename}")
@log_time
async def get_map_file(
    request: Request,
    map_filename: str,
    host: str = Header(...),
    profile: Profile = Depends(retrieve_profile(status_code=status.HTTP_404_NOT_FOUND)),
    session: Session = Depends(retrieve_session(status_code=status.HTTP_404_NOT_FOUND)),
):
    raw_path: str = request["raw_path"].decode()
    raw_path = raw_path.removeprefix("/osu")

    if usecases.songs_folder.valid_difficulty_adjusted_filename(map_filename):
        return Response(b"", status_code=status.HTTP_404_NOT_FOUND)

    return RedirectResponse(
        url=f"https://osu.ppy.sh{raw_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.post("/web/osu-submit-modular-selector.php")
@log_time
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
    # TODO: The things that is preventing all modes from being supported atm
    # Mod multiplers change across modes so implementing that
    # for out linear interpolation func, we'd need data points for each mode

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

        score_data, client_hash_decoded = (
            usecases.score_submission.decrypt_score_aes_data(
                score_data_b64=score_data_b64,
                client_hash_b64=client_hash_b64,
                iv_b64=iv_b64,
                osu_version=osu_version,
            )
        )
    except Exception as error:
        log.warning(f"Failed to parse submitted score payload: {error}")
        await usecases.sessions.notify_client(
            "Failed to parse submitted score. Please try again."
        )
        return Response(OsuErrors.NON.value.encode())

    if score_data.username.lower() != session.profile_name.lower():
        log.error(
            f"Score submission profile mismatch: score submitted for {score_data.username} but current session profile is {session.profile_name}"
        )
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

    osu_file = usecases.songs_folder.osu_file_for_beatmap(
        beatmap=beatmap,
        songs_folder=session.songs_folder,
    )

    if osu_file is None:
        await usecases.sessions.notify_client(
            "Failed to find .osu file for beatmap. Score may not have been saved, please relog and try again."
        )
        return Response(
            OsuErrors.BEATMAP.value.encode(),
        )

    # Store osu! file & audio file in osu_file.json incase of corrupted scores or data
    # TODO: Could take up too much space, is this necessary?
    # Is this much protection needed?
    await usecases.osu_files.store(osu_file)

    score = await usecases.score_submission.submit_score(
        score_id=await usecases.scores.generate_score_id(),
        map_file=osu_file,
        score_data=score_data,
        replay_frames=await replay_file.read(),
        beatmap_max_combo=beatmap.max_combo,
        beatmap_md5=beatmap.md5,
        calc_pp=beatmap.status.ranked(),
    )

    try:
        current_profile = await usecases.profiles.recalculate_stats(
            session.profile_name,
            max_combo=score.combo,
            game_mode=score.game_mode,
            server_settings=server_settings,
            scoring_algorithm=profile.settings.scoring_algorithm,
        )
    except OsuDailyCredentialsError:
        await usecases.sessions.silent_restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    # TODO: Support AP?
    if "RX" in score.enabled_mods:
        await usecases.sessions.update_current_session(
            session,
            update_client=True,
        )
        return Response(OsuErrors.NON.value.encode())

    (
        beatmap_ranking_chart,
        overall_ranking_chart,
    ) = await usecases.scores.get_ranking_charts(
        beatmap=beatmap,
        old_profile=profile,
        current_profile=current_profile,
        new_score=score,
        settings=profile.settings,
    )

    # TODO: Port bancho achievements here!
    unlocked_achievements = Achievements()

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

    await usecases.sessions.update_current_session(
        session,
        update_client=True,
    )

    return Response(content=submission_charts.serialize())


@osu.get("/web/osu-rate.php")
@log_time
async def osu_rate(
    map_md5: str = Query(..., alias="c"),
    rating: int | None = Query(None, alias="v"),
    profile: Profile = Depends(retrieve_profile(OsuErrors.NON)),
    session: Session = Depends(retrieve_session(OsuErrors.NON)),
    server_settings: ServerSettings = Depends(retrieve_server_settings),
):
    if session.songs_folder is None:
        await usecases.sessions.silent_restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    beatmap = await usecases.beatmaps.from_md5(
        beatmap_md5=map_md5,
        songs_folder=session.songs_folder,
        current_settings=profile.settings,
    )

    if beatmap is None or not beatmap.status.has_leaderboard():
        return Response(b"not ranked")

    if rating is None:
        # user hasn't rated the map, so just tell them they can submit a rating
        return Response(b"ok")

    return Response(f"alreadyvoted\n{beatmap.average_rating}".encode())


@osu.get("/web/osu-getreplay.php")
@log_time
async def get_replay(
    score_id: int = Query(..., alias="c"),
    mode: int = Query(..., alias="m"),
    profile: Profile = Depends(retrieve_profile(OsuErrors.NON)),
    session: Session = Depends(retrieve_session(OsuErrors.NON)),
):
    beatmap_md5 = session.latest_beatmap.md5 if session.latest_beatmap else None
    is_difficulty_adjusted = (
        session.latest_beatmap.is_difficulty_adjusted
        if session.latest_beatmap
        else False
    )

    if score_id > 0:
        if is_difficulty_adjusted:
            await usecases.sessions.notify_client(
                "Replays for difficulty adjusted scores are not available."
            )
            return Response(OsuErrors.NON.value.encode())

        if session.latest_beatmap is None:
            await usecases.sessions.notify_client(
                "No beatmap information found for replay request. Ensure you have recently accessed the beatmap's leaderboard and try again."
            )
            return Response(OsuErrors.NON.value.encode())

        lazer_score = score_id not in session.latest_beatmap.avaliable_replays
        if lazer_score:
            usecases.replay.open_lazer_score(
                score_id=score_id,
            )
            await usecases.sessions.notify_client(
                "Successfully opened lazer score in browser!"
            )
            return Response(OsuErrors.NON.value.encode())

        replay_data = await usecases.bancho_scores.get_replay(
            score_id=score_id,
            beatmap_md5=beatmap_md5,
        )

        if replay_data is None:
            await usecases.sessions.notify_client(
                "Replay data for this score is not available.\n"
                "Ensure this score was set on stable in order to view it's replay"
            )
            return Response(OsuErrors.NON.value.encode())

        return Response(content=replay_data)

    # since we encode our score ids to negative to
    # indicate a profile's score, so decode it
    score_id = abs(score_id)

    replay_frames = await usecases.scores.get_replay_frames_for_score_id(
        score_id=score_id
    )

    if replay_frames is None:
        await usecases.sessions.notify_client(
            "Replay data for this score is not available.\n"
            "To recover the replay, head to the score link & recover w/ right beatmap or something like that"
        )
        return Response(OsuErrors.NON.value.encode())

    return Response(content=replay_frames)


@osu.get("/web/osu-search.php")
@log_time
async def osu_direct(
    q: str = Query(..., alias="q"),
    mode: int = Query(..., alias="m"),
    ranked_status: int = Query(..., alias="r"),
    page_num: int = Query(..., alias="p"),
    session: Session = Depends(retrieve_session(OsuErrors.NON)),
):
    # TODO: current pagination process can be a lil broken cause
    # you could go scroll down in search
    # go to menu and then go back and the pagination wouldn't reset
    query = urlparse.unquote(q)
    if query in ("Newest", "Top+Rated", "Most+Played"):
        query = ""

    page_mode = osu_direct_mode_to_osu_api_v2(mode)
    status_type = osu_direct_ranked_status_to_osu_api_v2(ranked_status)

    if (query, page_mode, status_type) not in session.osu_client.previous_direct_search:
        session.osu_client.previous_direct_search = [(query, page_mode, status_type)]
        session.osu_client.direct_cursor_string = None
        await usecases.sessions.update_current_session(session)

    direct_response = await usecases.direct.page(
        query=query,
        status_type=status_type,
        mode=page_mode,
    )

    if direct_response is None:
        return Response(
            b"-1\nFailed to retrieve search results. Please try again later."
        )

    return Response(content=direct_response.serialize())


@osu.get("/d/{map_set_id}")
async def get_osz(
    map_set_id: str = Path(...),
) -> Response:
    # TODO: Figure out how to support video downloads
    # use playwrite and osu! credentials to get direct
    # download link for the osz file ?
    return RedirectResponse(
        url=f"https://osu.gatari.pw/d/{map_set_id}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


# Handles stuff like: osu://s/218851
@osu.get("/web/osu-search-set.php")
async def osu_scheme(
    map_set_id: int | None = Query(None, alias="s"),
    map_id: int | None = Query(None, alias="b"),
    checksum: str | None = Query(None, alias="c"),
):
    scheme_response = await usecases.direct.scheme(
        map_set_id=map_set_id,
        map_id=map_id,
        checksum=checksum,
    )

    return Response(content=scheme_response.serialize())
