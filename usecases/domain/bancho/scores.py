import asyncio

import ossapi.enums
import ossapi.models
from ossapi import UserCompact
from ossapi.enums import ScoreType

import usecases.domain.calculator.performance
from usecases.adapters.ossapiasync import OssapiAsync
from models.bancho.scores import Combo, LazerScore, Mods, Scores, StableScore
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
from models.domain.gameplay import osuGameMode
from models.domain.scores import AcceptedScores
from osuProtocol.client_web import ScoringAlgorithm
from osuProtocol.replay import extract_replay_frames_from_osr
from repositories.osufiles.songs_folder import OsuFileRepository


def api_is_score_lazer(score: ossapi.models.Score) -> bool:
    return not score.legacy_score_id


def api_to_score_id(score: ossapi.models.Score) -> int:
    if score.legacy_score_id:
        if score.id is not None:
            return score.id
        else:
            print(
                f"Score with legacy_score_id {score.legacy_score_id} is missing id field, defaulting score_id to 0"
            )
            return 0
    else:
        return score.id or 0


async def api_to_score_model(
    score: ossapi.models.Score,
    # beatmap: Beatmap,
    beatmap_md5: str,
    beatmap_id: int,
    beatmap_max_combo: int,
    game_mode: osuGameMode,
    scoring_algorithm: ScoringAlgorithm = ScoringAlgorithm.LAZER,  # TODO: safe?
    pp_calc_fallback: bool = True,
) -> StableScore | LazerScore:
    osu_file_resolver = OsuFileRepository()

    user: UserCompact = score._ossapi_data["_user"]

    if api_is_score_lazer(score):
        score_model = LazerScore
    else:
        score_model = StableScore

    score_id = api_to_score_id(score)
    score_mods = Mods.from_api_v2(score.mods)
    osu_file = await osu_file_resolver.from_md5(beatmap_md5)

    if osu_file is None:
        print(
            f"Could not find .osu file for beatmap {beatmap_id} with md5 {beatmap_md5}, "
            f"performance points will not be calculated for score {score_id}"
        )
        raise Exception

    if score.pp is None:
        if scoring_algorithm == ScoringAlgorithm.PP and pp_calc_fallback:
            pp = usecases.domain.calculator.performance.pp(
                map_file=osu_file,
                game_mode=game_mode,
                mods=score_mods,
                combo=score.max_combo,
                n300=score.statistics.great or 0,
                n100=score.statistics.ok or 0,
                n50=score.statistics.meh or 0,
                nmiss=score.statistics.miss or 0,
            )
        else:
            pp = 0  # TODO: is this right?
    else:
        pp = int(score.pp)

    return score_model(
        score_id=score_id,
        username=user.username,
        total_score_value=score.total_score,
        combo=Combo(actual=score.max_combo, max=beatmap_max_combo),
        count50=score.statistics.meh or 0,
        count100=score.statistics.ok or 0,
        count300=score.statistics.great or 0,
        count_miss=score.statistics.miss or 0,
        perfect=score.is_perfect_combo,
        enabled_mods=Mods(score_mods),
        user_id=user.id,
        time_set=int(score.ended_at.timestamp()),
        replay_available=score.has_replay,
        performance_points=pp,
        game_mode=game_mode,
    )


# @cached_for_10_minutes
async def get_score_for_user_on_beatmap(
    api_client: OssapiAsync,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    user_id: int,
    accepted_scores: AcceptedScores,
    scoring_algorithm: ScoringAlgorithm,
) -> StableScore | LazerScore | None:
    if accepted_scores == AcceptedScores.STABLE_ONLY:
        stable_only = True
    elif accepted_scores == AcceptedScores.LAZER_ONLY:
        stable_only = False
    elif accepted_scores == AcceptedScores.BOTH:
        stable_only = False

    try:
        beatmap_user_score = await api_client.beatmap_user_score(
            beatmap_id=beatmap.id,
            user_id=user_id,
            mode=game_mode.to_api_v2(),
            legacy_only=stable_only,
        )
    except Exception as e:
        if "`None`" in str(e):
            return None
        else:
            raise e

    if beatmap_user_score is None:
        # log.info(f"No score found for user {user_id} on beatmap {beatmap.id}")
        return None

    score = beatmap_user_score.score

    if score is None:
        # log.info(f"No score data found for user {user_id} on beatmap {beatmap.id}")
        return None

    score = await api_to_score_model(
        score=score,
        beatmap_md5=beatmap.md5,
        beatmap_id=beatmap.id,
        beatmap_max_combo=beatmap.max_combo,
        game_mode=game_mode,
        scoring_algorithm=scoring_algorithm,
    )

    # cache.score_for_user_on_beatmap_by_md5.set(beatmap.md5, score)

    return score


# @cached_for_10_minutes
async def get_friends_scores_for_beatmap(
    api_client: OssapiAsync,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    friends_user_ids: list[int],
    scoring_algorithm: ScoringAlgorithm,
) -> Scores:
    score_tasks = [
        get_score_for_user_on_beatmap(
            api_client=api_client,
            beatmap=beatmap,
            game_mode=game_mode,
            user_id=user_id,
            accepted_scores=accepted_scores,
            scoring_algorithm=scoring_algorithm,
        )
        for user_id in friends_user_ids
    ]

    results = await asyncio.gather(*score_tasks)

    friends_scores: list[StableScore | LazerScore] = [
        score
        for score in results
        if score is not None and not isinstance(score, Exception)
    ]

    return Scores(all_scores=friends_scores)


async def get_scores_for(
    api_client: OssapiAsync,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    scoring_algorithm: ScoringAlgorithm,
    mods: Mods | None = None,
) -> Scores:

    if accepted_scores == AcceptedScores.STABLE_ONLY:
        stable_only = True
    elif accepted_scores == AcceptedScores.LAZER_ONLY:
        stable_only = False
    elif accepted_scores == AcceptedScores.BOTH:
        stable_only = False

    if mods is not None:
        requested_mods = int(mods)
    else:
        requested_mods = None

    try:
        requested_scores = await api_client.beatmap_scores(
            beatmap_id=beatmap.id,
            mode=game_mode.to_api_v2(),
            mods=requested_mods,
            legacy_only=stable_only,
            type=scoring_algorithm.to_api_v2(),
        )
    except ValueError:
        # # log.error(f"Error fetching scores for beatmap {beatmap.id}: {e}")
        return Scores(all_scores=[])

    if not requested_scores:
        # # log.info(f"No scores found for beatmap {beatmap.id} with mods {mods} and ranking type {ranking_type}")
        return Scores(all_scores=[])

    scores = Scores(all_scores=[])

    for score in requested_scores.scores:
        if accepted_scores == AcceptedScores.LAZER_ONLY and not api_is_score_lazer(
            score
        ):
            continue

        if mods is not None:
            score_mods = Mods.from_api_v2(score.mods)

            if "NC" in mods and "NC" not in score_mods:
                continue

            if "DT" in mods and "NC" in score_mods:
                continue

        score_model = await api_to_score_model(
            score=score,
            beatmap_md5=beatmap.md5,
            beatmap_id=beatmap.id,
            beatmap_max_combo=beatmap.max_combo,
            game_mode=game_mode,
            scoring_algorithm=scoring_algorithm,
        )
        scores.append(score_model)

    return scores


async def get_any_scores_for(
    api_client: OssapiAsync,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    scoring_algorithm: ScoringAlgorithm,
) -> Scores:
    return await get_scores_for(
        api_client=api_client,
        beatmap=beatmap,
        game_mode=game_mode,
        accepted_scores=accepted_scores,
        mods=None,
        scoring_algorithm=scoring_algorithm,
    )


# @cached_for_10_minutes
async def get_mod_specific_scores_for(
    api_client: OssapiAsync,
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    mods: Mods,
    scoring_algorithm: ScoringAlgorithm,
) -> Scores:
    return await get_scores_for(
        api_client=api_client,
        beatmap=beatmap,
        game_mode=game_mode,
        accepted_scores=accepted_scores,
        mods=mods,
        scoring_algorithm=scoring_algorithm,
    )


# @cached_for_10_minutes
async def get_replay(
    api_client: OssapiAsync, score_id: int, beatmap_md5: str | None = None
) -> bytes | None:
    """Returns compatible stable replay frames for the given score ID or None if it doesn't match the conditions"""
    # Check if replay is available for this score & md5's match

    try:
        # Full replay payload
        replay_data = await api_client.download_score(
            score_id=score_id,
            raw=True,
        )

        assert replay_data is not None, "Expected replay data to be bytes"
        assert isinstance(replay_data, bytes), (
            f"Expected replay data to be bytes, got {type(replay_data)}"
        )

        # Extract replay frames from .osr replay data
        replay_frames, replay_beatmap_md5 = extract_replay_frames_from_osr(replay_data)

        if beatmap_md5 and replay_beatmap_md5 != beatmap_md5:
            print(
                f"Replay beatmap md5 {replay_beatmap_md5} does not match expected {beatmap_md5}"
            )
            return None
        else:
            return replay_frames

    except ValueError as e:
        # log.error(f"Error fetching replay for score {score_id}: {e}")
        raise


# @cached_for_five_minutes
async def get_recent_from(
    api_client: OssapiAsync,
    user_id: int,
    game_mode: osuGameMode,
) -> list[ossapi.models.Score]:

    recent_scores = await api_client.user_scores(
        user_id=user_id,
        type=ScoreType.RECENT,
        include_fails=True,
        mode=game_mode.to_api_v2(),
    )

    filtered_scores: list[ossapi.models.Score] = []

    for score in recent_scores:
        if score.beatmap is None:
            continue

        if score.beatmap.checksum is None:
            continue

        filtered_scores.append(score)

    return filtered_scores
