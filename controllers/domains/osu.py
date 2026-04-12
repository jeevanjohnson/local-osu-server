import urllib.parse
import urllib.parse as urlparse
import webbrowser

import orjson
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

import services.osu
import usecases.application.client.update

# from adapters import log_time
from controllers.dependencies import (
    client_state,
    profile,
    retrieve_server_settings,
)
from models.database.client.state import ClientState
from models.database.profiles import CurrentProfile as Profile
from models.database.server_settings import CurrentServerSettings as ServerSettings
from models.domain.errors import OsuErrors
from models.domain.gameplay import Mods, osuGameMode
from osu_protocol.osu.direct import (
    osu_direct_mode_to_osu_api_v2,
    osu_direct_ranked_status_to_osu_api_v2,
)
from osu_protocol.osu.types import (
    LeaderboardType,
)

osu = APIRouter(
    prefix="/osu",
)


@osu.get("/web/osu-getseasonal.php")
# log
async def get_seasonal_backgrounds(
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    response = await services.osu.process_seasonal_backgrounds_request(
        seasonal_background_urls=profile.seasonal_backgrounds if profile else [],
    )

    return Response(content=orjson.dumps(response))


@osu.get("/beatmap{full_path:path}")
# log
async def get_beatmap(
    full_path: str,
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    response = await services.osu.process_beatmap_request(full_path=full_path)

    return RedirectResponse(
        url=response,
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.get("/users/{user_id}")
# log
async def get_user_page(
    user_id: int = Path(...),
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    response = await services.osu.process_user_page_request(user_id=user_id)
    return RedirectResponse(
        url=response,
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.get("/home/account/edit")
# log
async def get_avatar_page(
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    response = await services.osu.process_avatar_page_request()

    return RedirectResponse(
        url=response,
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )


@osu.get("/web/osu-osz2-getscores.php")
# log
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
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    if profile is None:
        await usecases.application.client.update.restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    leaderboard = await services.osu.process_leaderboard_request(
        client_state=client_state,
        profile=profile,
        leaderboard_type=LeaderboardType(leaderboard_type),
        map_md5=map_md5,
        map_filename=urllib.parse.unquote(map_filename),
        mode_arg=osuGameMode(mode_arg),
        map_set_id=map_set_id,
        mods_arg=Mods.from_stable_mods(mods_arg),
    )

    return Response(content=leaderboard.serialize())


@osu.get("/web/maps/{map_filename}")
# log
async def get_map_file(
    request: Request,
    map_filename: str,
    host: str = Header(...),
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    response = await services.osu.process_map_file_request(
        url_path=request["raw_path"].decode().removeprefix("/osu"),
        map_filename=map_filename,
    )

    if response["status_code"] == 404:
        return Response(status_code=404)
    else:
        return RedirectResponse(
            url=response["url"],
            status_code=response["status_code"],
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
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    if profile is None:
        await usecases.application.client.update.restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    response = await services.osu.process_modular_selector_submission(
        raw_score_parameters=await request.form(),
        client_hash_b64=client_hash_b64,
        iv_b64=iv_b64,
        osu_version=osu_version,
        client_state=client_state,
        profile=profile,
    )

    if isinstance(response, OsuErrors):
        return Response(content=response.value.encode())

    return Response(content=response.serialize())


@osu.get("/web/osu-rate.php")
# log
async def osu_rate(
    map_md5: str = Query(..., alias="c"),
    rating: int | None = Query(None, alias="v"),
    profile: Profile | None = Depends(profile),
    client_state: ClientState = Depends(client_state),
):
    if profile is None:
        await usecases.application.client.update.restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    response = await services.osu.process_rating_submission(
        map_md5=map_md5,
        rating=rating,
        client_state=client_state,
    )

    return Response(content=response.encode())


@osu.get("/web/osu-getreplay.php")
# log
async def get_replay(
    score_id: int = Query(..., alias="c"),
    mode: int = Query(..., alias="m"),
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    if profile is None:
        await usecases.application.client.update.restart_client()
        return Response(
            OsuErrors.NON.value.encode(),
        )

    response = await services.osu.process_replay_request(
        score_id=score_id,
        client_state=client_state,
    )

    return Response(content=response)


@osu.get("/web/osu-search.php")
# log
async def osu_direct(
    q: str = Query(..., alias="q"),
    mode: int = Query(..., alias="m"),
    ranked_status: int = Query(..., alias="r"),
    page_num: int = Query(..., alias="p"),
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
):
    query = urlparse.unquote(q)
    if query in ("Newest", "Top+Rated", "Most+Played"):
        query = ""

    page_mode = osu_direct_mode_to_osu_api_v2(mode)
    status_type = osu_direct_ranked_status_to_osu_api_v2(ranked_status)

    response = await services.osu.process_direct_search_result_request(
        query=query,
        page_mode=page_mode,
        status_type=status_type,
        client_state=client_state,
    )

    if response is None:
        return Response(
            b"-1\nFailed to retrieve search results. Please try again later."
        )

    return Response(content=response.serialize())


@osu.get("/d/{map_set_id}")
async def get_osz(
    map_set_id: str = Path(...),
    server_settings: ServerSettings = Depends(retrieve_server_settings),
    client_state: ClientState = Depends(client_state),
    profile: Profile | None = Depends(profile),
) -> Response:
    url = await services.osu.process_osz_request(
        map_set_id=int(map_set_id),
        beatmap_mirror=server_settings.attempt_beatmap_mirror_downloads,
    )

    if "osu.ppy.sh" not in url:
        return RedirectResponse(
            url=url,
            status_code=status.HTTP_301_MOVED_PERMANENTLY,
        )
    else:
        webbrowser.open(url)
        return Response(OsuErrors.NON.value.encode())


# Handles stuff like: osu://s/218851
@osu.get("/web/osu-search-set.php")
async def osu_scheme(
    map_set_id: int | None = Query(None, alias="s"),
    map_id: int | None = Query(None, alias="b"),
    checksum: str | None = Query(None, alias="c"),
):
    scheme_response = await services.osu.process_scheme_request(
        map_set_id=map_set_id,
        map_id=map_id,
    )

    if scheme_response is None:
        return Response(
            OsuErrors.BEATMAP.value.encode(),
        )

    return Response(content=scheme_response.serialize())
