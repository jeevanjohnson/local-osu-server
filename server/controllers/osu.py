from fastapi import APIRouter, Depends, Path, Query, Response, status, Header
from typing import Literal
from core.osu_protocol.osu.leaderboard import NotSubmittedLeaderboard, UpdateBeatmapRequestLeaderboard, GraveyardLeaderboard
import server.dependencies as dependencies
from core.usecases.domain.player import Player
import orjson
from fastapi.responses import RedirectResponse
import core.usecases.domain.port as port_usecases
import core.usecases.domain.client_state as client_state_usecases
from core.models.domain.gameplay.game_mode import GameMode
from core.models.domain.gameplay.mods import Mods
import core.usecases.application.beatmaps as beatmap_usecases
from core.usecases.application.beatmaps import BeatmapStatus
import core.usecases.application.leaderboards as leaderboards_usecases
from core.osu_protocol.osu.types import LeaderboardType
from core.usecases.domain.osu_api import InvalidOsuApiCredentialsError
import time

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
    
    if player.name in beatmap.status_override:
        beatmap_status = beatmap.status_override[player.name]
    else:
        beatmap_status = beatmap.status
    
    if not beatmap_status.has_leaderboards():
        leaderboard = GraveyardLeaderboard()
        return Response(
            leaderboard.serialize()
        )

    client_state.beatmap.md5 = beatmap.md5
    client_state.beatmap.id = beatmap.osu_id
    client_state.beatmap.set_id = beatmap.osu_set_id
    client_state.beatmap.is_difficulty_adjusted = beatmap.difficulty_adjusted

    client_state = player.update_client_state(client_state)

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
