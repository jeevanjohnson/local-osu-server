from fastapi import APIRouter, Response, Query
from ossapi import UserCompact
from fastapi.responses import RedirectResponse
from constants import SEASONAL_BG_GIT_URL
import json
import usecases.profiles
from fastapi import status
from osuProtocol.server_packets import osuGameMode, osuMods
import usecases.sessions
from osuProtocol.client_web import LeaderboardType, osuMapStatus
import usecases.scores
import usecases.beatmaps
from osuProtocol.server_packets import PlayerStats as ServerPlayerStats, Notification
from osuProtocol.client_web import LeaderboardScore, LeaderboardHeader, Leaderboard
from osuProtocol.client_web import GraveyardLeaderboard, ScoringAlgorithm

osu = APIRouter(
    prefix="/osu",
)

NULL_RESPONSE = Response(b'error: no')

# osu is weird for this
@osu.get("/web/osu-getseasonal.php")
async def get_seasonal_backgrounds():
    return Response(
        content=json.dumps([SEASONAL_BG_GIT_URL])
    )

@osu.get("/beatmaps/{full_path:path}")
async def get_beatmap(full_path: str):
    return RedirectResponse(
        url=f"https://osu.ppy.sh/beatmaps/{full_path}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY
    )

@osu.get('/web/osu-osz2-getscores.php')
async def get_leaderboard(
    requesting_from_editor_song_select: bool = Query(..., alias="s"),
    leaderboard_version: int = Query(..., alias="vv"),
    leaderboard_type: int = Query(..., alias="v"),
    map_md5: str = Query(..., alias="c"),
    map_filename: str = Query(..., alias="f"),
    mode_arg: int = Query(..., alias="m"),
    map_set_id: int = Query(..., alias="i",),
    mods_arg: int = Query(..., alias="mods"),
    map_package_hash: str = Query(..., alias="h"),
    aqn_files_found: bool = Query(..., alias="a"),
):
    session = usecases.sessions.get_current_session()
    if session is None or session["profile_name"] is None:
        return NULL_RESPONSE
    
    profile = usecases.profiles.get_profile(session["profile_name"])
    if profile is None:
        return NULL_RESPONSE
    
    profile_data = profile[session["profile_name"]]
    leaderboard_type = LeaderboardType(leaderboard_type)
    mode_arg = osuGameMode(mode_arg)

    if session["current_game_mode"] != mode_arg.value:
        session["current_game_mode"] = mode_arg.value

        usecases.sessions.update_current_session(session)
        usecases.sessions.update_in_game_stats()

    beatmap = usecases.beatmaps.get_beatmap(beatmap_md5=map_md5, beatmap_id=map_set_id)
    if beatmap is None:
        return Response(
            GraveyardLeaderboard().serialize()
        )

    beatmap_set = usecases.beatmaps.get_beatmap_set(
        beatmap_set_id=beatmap.beatmapset_id
    )

    if beatmap_set is None:
        usecases.sessions.enqueue_packets_to_current_session(
            Notification("Beatmap found, but not set?, Notify Dev")
        )
        return Response(b'error: no')

    mods = osuMods(mods_arg)

    if profile_data["settings"]["leaderboard"]["show_lazer_scores_on_leaderboard"]:
        legacy_leaderboard = False
    else:
        legacy_leaderboard = True

    scores = usecases.scores.get_scores_for_beatmap(
        leaderboard_type=leaderboard_type,
        game_mode=mode_arg,
        mods=mods,
        limit=profile_data["settings"]["leaderboard"]["leaderboard_score_limit"],
        legacy_leaderboard=legacy_leaderboard,
        beatmap_md5=map_md5,
        beatmap_id=map_set_id
    )

    if scores is None:
        total_scores = 0
    else:
        total_scores = len(scores)

    # TODO: handle map updates

    leaderboard_header = LeaderboardHeader(
        beatmap_status=osuMapStatus.from_api_v2_ranked_status(beatmap.ranked),
        beatmap_id=beatmap.id,
        beatmap_set_id=beatmap.beatmapset_id,
        num_of_scores=total_scores,
        artist=beatmap_set.artist_unicode,
        title=beatmap_set.title_unicode
    )

    leaderboard = Leaderboard(
        header=leaderboard_header,
        scores=[]
    )

    leaderboard_scores = []

    if not scores:
        return Response(
            content=leaderboard.serialize()
        )

    scoring_algorithm = ScoringAlgorithm(profile_data["settings"]["scoring_algorithm"])

    # removes potential stable / lazer crossovers
    scores.remove_duplicates()

    scores.set_scoring_algorithm(scoring_algorithm)
    scores.sort_by_algorithm()

    score_limit = profile_data["settings"]["leaderboard"]["leaderboard_score_limit"]
    scores = scores[:score_limit]

    for index, score in enumerate(scores):
        leaderboard_score = LeaderboardScore.from_score(score, index + 1)
        leaderboard_scores.append(leaderboard_score)

    leaderboard.scores = leaderboard_scores

    return Response(
        content=leaderboard.serialize()
    )

