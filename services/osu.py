import json
from typing import TypedDict

import ossapi.enums
from fastapi.datastructures import FormData

import usecases.application.beatmaps
import usecases.application.client.state
import usecases.application.client.update
import usecases.application.direct
import usecases.application.leaderboards
import usecases.application.replays
import usecases.domain.osufile
from constants.network import LOS_INTERFACE_PORT
from models.database.client.state import ClientState
from models.database.profiles import CurrentProfile as Profile
from models.domain.errors import OsuErrors
from models.domain.gameplay import Mods, osuGameMode
from models.domain.scores import AcceptedScores
from osuProtocol.client_web import (
    DirectBeatmapSet,
    DirectSearchResult,
    GraveyardLeaderboard,
    Leaderboard,
    LeaderboardType,
    NotSubmittedLeaderboard,
    UpdateBeatmapRequestLeaderboard,
)


async def process_seasonal_backgrounds_request(
    seasonal_background_urls: list[str],
) -> str:
    return json.dumps(seasonal_background_urls)


async def process_beatmap_request(
    full_path: str,
) -> str:
    return f"https://osu.ppy.sh/beatmap{full_path}"


async def process_user_page_request(
    user_id: int,
) -> str:
    if user_id != 2:
        return f"https://osu.ppy.sh/users/{user_id}"
    else:
        return f"http://localhost:{LOS_INTERFACE_PORT}/dashboard/"


async def process_avatar_page_request() -> str:
    return f"http://localhost:{LOS_INTERFACE_PORT}/dashboard/"


async def process_leaderboard_request(
    leaderboard_type: LeaderboardType,
    map_md5: str,
    map_filename: str,
    mode_arg: osuGameMode,
    map_set_id: int,
    client_state: ClientState,
    mods_arg: Mods,
    profile: Profile,
) -> Leaderboard:
    # if we are on the leaderboard, make sure our direct search history is cleared since it's not relevant anymore
    client_state.direct_reference.last_query = []
    client_state.direct_reference.cursor_string = None

    if client_state.game_mode != mode_arg:
        client_state.game_mode = mode_arg
        await usecases.application.client.update.stats_with_state_and_profile(
            client_state=client_state, profile=profile
        )

    await usecases.application.client.state.update(client_state)

    beatmap = await usecases.application.beatmaps.from_leaderboard_request(
        beatmap_md5=map_md5,
        beatmap_set_id=map_set_id,
        map_filename=map_filename,
        profile_name=client_state.profile_name,
    )

    if beatmap is None:
        client_state.beatmap.md5 = ""
        client_state.beatmap.id = 0
        client_state.beatmap.set_id = 0
        client_state.beatmap.is_difficulty_adjusted = False
        client_state.beatmap.watchable_replays = []

        await usecases.application.client.state.update(client_state)
        return UpdateBeatmapRequestLeaderboard()

    if beatmap.unsubmitted:
        client_state.beatmap.md5 = ""
        client_state.beatmap.id = 0
        client_state.beatmap.set_id = 0
        client_state.beatmap.is_difficulty_adjusted = False
        client_state.beatmap.watchable_replays = []
        await usecases.application.client.state.update(client_state)
        return NotSubmittedLeaderboard()

    client_state.beatmap.md5 = beatmap.md5
    client_state.beatmap.id = beatmap.id
    client_state.beatmap.set_id = beatmap.set_id
    client_state.beatmap.is_difficulty_adjusted = beatmap.difficulty_adjusted

    client_state.beatmap.watchable_replays = []  # TODO: just wait

    await usecases.application.client.state.update(client_state)

    bmap_status = beatmap.status[client_state.profile_name]

    if not bmap_status.has_leaderboard():
        return GraveyardLeaderboard()

    accepted_scores = AcceptedScores.BOTH

    if not profile.settings.leaderboard.show_lazer_scores_on_leaderboard:
        accepted_scores = AcceptedScores.STABLE_ONLY

    if profile.settings.scoring.score_v2_shows_lazer_only_leaderboard:
        if "SV2" in mods_arg:
            accepted_scores = AcceptedScores.LAZER_ONLY

    return await usecases.application.leaderboards.from_request(
        beatmap=beatmap,
        leaderboard_type=leaderboard_type,
        game_mode=mode_arg,
        profile=profile,
        profile_name=client_state.profile_name,
        accepted_scores=accepted_scores,
        mods=mods_arg,
    )


class MapFileRequestResponse(TypedDict):
    url: str
    status_code: int


async def process_map_file_request(
    url_path: str,
    map_filename: str,
) -> MapFileRequestResponse:
    if usecases.domain.osufile.valid_difficulty_adjusted_filename(map_filename):
        return MapFileRequestResponse(url="ignore update request", status_code=404)

    return MapFileRequestResponse(url=f"https://osu.ppy.sh{url_path}", status_code=301)


import usecases.application.score_submission
import usecases.domain.beatmaps
import usecases.domain.osufile
import usecases.domain.score_submission
import usecases.domain.scores
from osuProtocol.client_web import SubmissionCharts


async def process_modular_selector_submission(
    raw_score_parameters: FormData,
    client_hash_b64: bytes,
    iv_b64: bytes,
    osu_version: str,
    client_state: ClientState,
    profile: Profile,
) -> OsuErrors | SubmissionCharts:
    charts, score_id = await usecases.application.score_submission.process_submission(
        raw_score_parameters=raw_score_parameters,
        client_hash_b64=client_hash_b64,
        iv_b64=iv_b64,
        osu_version=osu_version,
        profile=profile,
        profile_name=client_state.profile_name,
    )

    client_state.loaded_score_id = score_id
    await usecases.application.client.state.update(client_state)

    return charts


async def process_rating_submission(
    map_md5: str, rating: int | None, client_state: ClientState
) -> str:
    beatmap = await usecases.application.beatmaps.from_md5(
        beatmap_md5=map_md5, profile_name=client_state.profile_name
    )

    if beatmap is None:
        return "not ranked"

    bmap_status = beatmap.status[client_state.profile_name]
    if not bmap_status.has_leaderboard():
        return "not ranked"

    if rating is None:
        # user hasn't rated the map, so just tell them they can submit a rating
        return "ok"

    return f"alreadyvoted\n{beatmap.average_rating}"


async def process_replay_request(
    score_id: int,
    client_state: ClientState,
) -> bytes:
    beatmap_md5 = client_state.beatmap.md5
    is_difficulty_adjusted = client_state.beatmap.is_difficulty_adjusted

    if score_id > 0:
        replay_data = await usecases.application.replays.get_bancho_replay(
            score_id=score_id,
            beatmap_md5=beatmap_md5,
            is_difficulty_adjusted=is_difficulty_adjusted,
            available_replays=client_state.beatmap.watchable_replays,
        )
        if isinstance(replay_data, str):
            await usecases.application.client.update.notify(replay_data)
            return OsuErrors.NON.value.encode()

        return replay_data

    replay_frames = await usecases.domain.scores.get_replay_frames_for_score_id(
        score_id=abs(score_id)
    )

    client_state.loaded_score_id = score_id
    await usecases.application.client.state.update(client_state)
    await usecases.application.client.update.notify(f"Watching score: {score_id}")

    if replay_frames is None:
        await usecases.application.client.update.notify(
            "Replay data for this score is not available."
        )
        return OsuErrors.NON.value.encode()

    return replay_frames


async def process_direct_search_result_request(
    query: str,
    page_mode: ossapi.enums.BeatmapsetSearchMode,
    status_type: ossapi.enums.BeatmapsetSearchCategory,
    client_state: ClientState,
) -> DirectSearchResult | None:
    if (query, page_mode, status_type) not in client_state.direct_reference.last_query:
        client_state.direct_reference.last_query = [(query, page_mode, status_type)]
        client_state.direct_reference.cursor_string = None
        await usecases.application.client.state.update(client_state)

    direct_response, cursor_string = await usecases.application.direct.page(
        query=query,
        status_type=status_type,
        mode=page_mode,
    )

    if direct_response is None:
        return None

    print(f"DEBUG service - cursor_string returned from API: {cursor_string}", )

    if cursor_string is not None:
        print(f"DEBUG service - storing cursor for next pagination", )
        client_state.direct_reference.cursor_string = cursor_string
        await usecases.application.client.state.update(client_state)
        print(f"DEBUG service - cursor stored in state", )
    else:
        print(f"DEBUG service - no cursor returned from API", )

    return direct_response


async def process_osz_request(
    map_set_id: int,
    beatmap_mirror: bool,
) -> str:
    if beatmap_mirror:
        return f"https://osu.gatari.pw/d/{map_set_id}"

    await usecases.application.client.update.notify(
        "Redirecting to osu.ppy.sh for beatmap download."
    )

    return f"https://osu.ppy.sh/beatmapsets/{map_set_id}/download"


async def process_scheme_request(
    map_set_id: int | None = None,
    map_id: int | None = None,
) -> DirectBeatmapSet | None:
    scheme_response = await usecases.application.direct.scheme(
        map_set_id=map_set_id,
        map_id=map_id,
    )

    return scheme_response
