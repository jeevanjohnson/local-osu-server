import json
import urllib.parse as urlparse

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import RedirectResponse

import usecases.beatmaps
import usecases.profiles
import usecases.scores
import usecases.sessions
from constants import SEASONAL_BG_GIT_URL
from models.database.sessions import CurrentSessionBeatmapInfo as SessionBeatmapInfo
from osuProtocol.client_web import (
    GraveyardLeaderboard,
    Leaderboard,
    LeaderboardHeader,
    LeaderboardScore,
    LeaderboardType,
    ScoringAlgorithm,
)
from osuProtocol.server_packets import osuGameMode, osuMods

osu = APIRouter(
    prefix="/osu",
)

NULL_RESPONSE = Response(b"error: no")


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
):
    map_filename = urlparse.unquote(map_filename)

    session = usecases.sessions.get_current_session()
    if session is None:
        return NULL_RESPONSE

    profile = usecases.profiles.get_profile(session.profile_name)
    if profile is None:
        return NULL_RESPONSE

    if session.songs_folder is None:
        return NULL_RESPONSE  # TODO: should never happen, so something is up with architecture if it does.

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

    scores = await usecases.scores.get_scores_for(
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
        )
        leaderboard_scores.append(leaderboard_score)

    leaderboard.scores = leaderboard_scores

    return Response(content=leaderboard.serialize())
