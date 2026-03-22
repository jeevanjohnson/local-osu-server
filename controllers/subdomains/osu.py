import json
import urllib.parse as urlparse

from fastapi import (
    APIRouter,
    Query,
    Response,
    status,
    Header,
    Form,
    File,
    Request,
    Depends,
)
from fastapi.responses import RedirectResponse
import usecases.scores

from models.database.profiles import CurrentProfile as Profile
from models.database.sessions import (
    CurrentSession as Session,
)
from models.database.scores import (
    CurrentScore as Score,
)
import usecases.beatmaps
import usecases.profiles
import usecases.bancho_scores
import usecases.sessions
import usecases.score_submission
from constants import SEASONAL_BG_GIT_URL
from models.database.sessions import CurrentSessionBeatmapInfo as SessionBeatmapInfo
from models.domain.gameplay import osuGameMode, osuMods
from osuProtocol.client_web import (
    GraveyardLeaderboard,
    Leaderboard,
    LeaderboardHeader,
    LeaderboardScore,
    LeaderboardType,
    ScoringAlgorithm,
)
from controllers.dependencies import retrive_profile, retrive_session, OsuErrors
from osupyparser.osr.osr_parser import ReplayFile

osu = APIRouter(
    prefix="/osu",
)


# osu is weird for this
@osu.get("/web/osu-getseasonal.php")
async def get_seasonal_backgrounds():
    return Response(content=json.dumps([SEASONAL_BG_GIT_URL]))


@osu.get("/beatmaps/{full_path:path}")
async def get_beatmap(full_path: str):
    return RedirectResponse(
        url=f"https://osu.ppy.sh/beatmaps/{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.get("/web/osu-osz2-getscores.php")
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
    profile: Profile = Depends(retrive_profile(OsuErrors.NON)),
    session: Session = Depends(retrive_session(OsuErrors.NON)),
):
    map_filename = urlparse.unquote(map_filename)

    if session.songs_folder is None:
        usecases.sessions.notify_client(
            "Failed to retrieve songs folder. Session data may be corrupted, please relog."
        )
        return Response(
            OsuErrors.NON.value.encode(),
        )

    leaderboard_type = LeaderboardType(leaderboard_type)
    mode_arg = osuGameMode(mode_arg)

    if session.current_game_mode != mode_arg:
        session.current_game_mode = mode_arg

        usecases.sessions.update_current_session(session, update_client=True)

    beatmap = await usecases.beatmaps.from_leaderboard_request(
        beatmap_md5=map_md5,
        beatmap_set_id=map_set_id,
        map_filename=map_filename,
        songs_folder=session.songs_folder,
        current_settings=profile.settings,
    )
    if beatmap is None:
        session.latest_beatmap = None
        usecases.sessions.update_current_session(session)

        return Response(GraveyardLeaderboard().serialize())

    session.latest_beatmap = SessionBeatmapInfo(
        id=beatmap.id,
        md5=beatmap.md5,
        set_id=beatmap.set_id,
    )

    usecases.sessions.update_current_session(session)

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


@osu.post("/web/osu-submit-modular-selector.php")
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
    profile: Profile = Depends(retrive_profile(OsuErrors.NON)),
    session: Session = Depends(retrive_session(OsuErrors.NON)),
):
    if session.songs_folder is None:
        usecases.sessions.notify_client(
            "Failed to retrieve songs folder. Session data may be corrupted, please relog."
        )
        return Response(
            OsuErrors.NON.value.encode(),
        )

    score_parameters = usecases.score_submission.parse_form_data(
        await request.form(),
    )

    if score_parameters is None:
        return Response(b"")

    score_data_b64, replay_file = score_parameters

    score_data, client_hash_decoded = usecases.score_submission.decrypt_score_aes_data(
        score_data_b64=score_data_b64,
        client_hash_b64=client_hash_b64,
        iv_b64=iv_b64,
        osu_version=osu_version,
    )

    beatmap = await usecases.beatmaps.from_score_submission_request(
        beatmap_md5=score_data.beatmap_md5,
        songs_folder=session.songs_folder,
        current_settings=profile.settings,
    )

    if beatmap is None:
        usecases.sessions.notify_client(
            "Failed to find beatmap for submitted score. Score may not have been saved, please relog and try again."
        )
        return Response(
            OsuErrors.BEATMAP.value.encode(),
        )

    # build score object
    score_id = usecases.scores.generate_score_id()

    replay = ReplayFile.from_bytes(await replay_file.read(), pure_lzma=True)

    score = Score.from_score_submission(
        score_id=score_id,
        score_data=score_data,
        replay_file=replay,
        map_file=beatmap.file,
        beatmap_md5=beatmap.md5,
    )

    # TODO: FINISH SCORE SUB 