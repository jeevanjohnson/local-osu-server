import asyncio
import time
from enum import Enum
from typing import Any

import ossapi.enums
import ossapi.models
from ossapi import UserCompact

import cache
from adapters import log
from models.bancho.scores import Combo, LazerScore, Mods, Scores, StableScore
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
from models.domain.gameplay import osuGameMode
from osuProtocol.client_web import LeaderboardType
from osuProtocol.replay import extract_replay_frames_from_osr
from usecases.providers import get_ossapi_async


class AcceptedScores(Enum):
    LAZER_ONLY = "lazer_only"
    STABLE_ONLY = "stable_only"
    BOTH = "both"


_SCORE_HOT_CACHE_TTL_SECONDS = 300
_SCORE_HOT_CACHE_MAX_SIZE = 1024
_score_hot_cache: dict[tuple[Any, ...], tuple[float, Scores, list[int]]] = {}
_score_inflight_requests: dict[
    tuple[Any, ...], asyncio.Task[tuple[Scores, list[int]]]
] = {}


def _make_score_cache_key(
    beatmap_id: int,
    game_mode: osuGameMode,
    leaderboard_type: LeaderboardType,
    stable_only: bool,
    ranking_type: ossapi.enums.RankingType,
    req_mods: int | None,
    req_limit: int,
    lazer_only: bool,
) -> tuple[Any, ...]:
    return (
        beatmap_id,
        int(game_mode),
        int(leaderboard_type),
        stable_only,
        str(ranking_type),
        req_mods,
        req_limit,
        lazer_only,
    )


def _get_cached_scores(cache_key: tuple[Any, ...]) -> tuple[Scores, list[int]] | None:
    cached = _score_hot_cache.get(cache_key)
    if cached is None:
        return None

    cached_at, cached_scores, cached_stable_ids = cached
    if time.monotonic() - cached_at > _SCORE_HOT_CACHE_TTL_SECONDS:
        _score_hot_cache.pop(cache_key, None)
        return None

    return cached_scores, list(cached_stable_ids)


def _cache_scores(
    cache_key: tuple[Any, ...], scores: Scores, stable_ids: list[int]
) -> None:
    if cache_key in _score_hot_cache:
        _score_hot_cache.pop(cache_key, None)

    if len(_score_hot_cache) >= _SCORE_HOT_CACHE_MAX_SIZE:
        oldest_key = next(iter(_score_hot_cache))
        _score_hot_cache.pop(oldest_key, None)

    _score_hot_cache[cache_key] = (time.monotonic(), scores, list(stable_ids))


class ScoresResolver: ...


def parse_difficulty_adjustment_settings(mod_settings: dict[str, Any]) -> list[str]:
    settings = []

    modifications = [
        ("cs_change", "CS"),
        ("approach_rate", "AR"),
        ("drain_rate", "HP"),
        ("overall_difficulty", "OD"),
    ]

    for setting_key, setting_prefix in modifications:
        setting_value = mod_settings.get(setting_key)
        if setting_value is not None:
            setting_value_length = len(str(setting_value))

            if setting_value_length > 4:
                setting_value = round(setting_value, 2)

            settings.append(f"{setting_prefix}{setting_value}")

    return settings


def api_is_score_lazer(score: ossapi.models.Score) -> bool:
    return not score.legacy_score_id


def api_to_mods(mods: list[ossapi.models.NonLegacyMod]) -> Mods:
    score_mods = []
    for mod in mods:
        mod_settings: dict[str, Any] = mod.settings

        if mod_settings:
            try:
                score_mods.append(mod.acronym)

                if mod_settings.get("speed_change"):
                    speed_change = mod_settings["speed_change"]
                    if speed_change != 1.5 and speed_change != 0.75:
                        score_mods.append(f"{speed_change}x")

                if mod.acronym == "DA":
                    score_mods.extend(
                        parse_difficulty_adjustment_settings(mod_settings)
                    )

            except Exception as e:
                log.warning(
                    f"Error processing mod settings for mod {mod.acronym}: {e}\nMod settings: {mod.settings}"
                )
        else:
            score_mods.append(mod.acronym)

    return Mods(score_mods)


def api_to_score_id(score: ossapi.models.Score) -> int:
    if score.legacy_score_id:
        if score.id is not None:
            return score.id
        else:
            log.warning(
                f"Score with legacy_score_id {score.legacy_score_id} is missing id field, defaulting score_id to 0"
            )
            return 0
    else:
        return score.id or 0


def api_to_score_model(
    score: ossapi.models.Score,
    beatmap_max_combo: int,
    game_mode: osuGameMode,
) -> StableScore | LazerScore:
    user: UserCompact = score._ossapi_data["_user"]

    if api_is_score_lazer(score):
        score_model = LazerScore
    else:
        score_model = StableScore

    score_id = api_to_score_id(score)
    score_mods = api_to_mods(score.mods)

    if score.pp is None:
        pp = 0
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


async def get_score_for_user_on_beatmap(
    beatmap: Beatmap,
    game_mode: osuGameMode,
    user_id: int,
    accepted_scores: AcceptedScores,
) -> StableScore | LazerScore | None:
    score = cache.score_for_user_on_beatmap_by_md5.get(beatmap.md5)
    if score is not None:
        return score

    osuApi = await get_ossapi_async()

    if accepted_scores == AcceptedScores.STABLE_ONLY:
        stable_only = True
    elif accepted_scores == AcceptedScores.LAZER_ONLY:
        stable_only = False
    elif accepted_scores == AcceptedScores.BOTH:
        stable_only = False

    try:
        beatmap_user_score = await osuApi.beatmap_user_score(
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
        log.info(f"No score found for user {user_id} on beatmap {beatmap.id}")
        return None

    score = beatmap_user_score.score

    if score is None:
        log.info(f"No score data found for user {user_id} on beatmap {beatmap.id}")
        return None

    score = api_to_score_model(score, beatmap.max_combo, game_mode)

    cache.score_for_user_on_beatmap_by_md5.set(beatmap.md5, score)

    return score


async def get_friends_scores_for_beatmap(
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    friends_user_ids: list[int],
) -> Scores:
    cached_scores = cache.friends_scores_for_beatmap_by_md5.get(beatmap.md5)
    if cached_scores is not None:
        return cached_scores

    friends_scores: list[StableScore | LazerScore] = []

    for user_id in friends_user_ids:
        bancho = await get_score_for_user_on_beatmap(
            beatmap=beatmap,
            game_mode=game_mode,
            user_id=user_id,
            accepted_scores=accepted_scores,
        )

        if bancho is None:
            continue

        friends_scores.append(bancho)

    scores = Scores(all_scores=friends_scores)

    cache.friends_scores_for_beatmap_by_md5.set(beatmap.md5, scores)

    return scores


async def get_scores_for(
    beatmap: Beatmap,
    game_mode: osuGameMode,
    ranking_type: ossapi.enums.RankingType,
    accepted_scores: AcceptedScores,
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

    osuApi = await get_ossapi_async()

    try:
        requested_scores = await osuApi.beatmap_scores(
            beatmap_id=beatmap.id,
            mode=game_mode.to_api_v2(),
            mods=requested_mods,
            legacy_only=stable_only,
            type=ranking_type,
        )
    except ValueError as e:
        # log.error(f"Error fetching scores for beatmap {beatmap.id}: {e}")
        return Scores(all_scores=[])

    if not requested_scores:
        # log.info(f"No scores found for beatmap {beatmap.id} with mods {mods} and ranking type {ranking_type}")
        return Scores(all_scores=[])

    scores = Scores(all_scores=[])

    for score in requested_scores.scores:
        # log.info(f"Fetched score with ID {score.id} for user {score._ossapi_data['_user'].username} with mods {[mod.acronym for mod in score.mods]}")

        scores.append(api_to_score_model(score, beatmap.max_combo, game_mode))

    return scores


async def get_any_scores_for(
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    ranking_type: ossapi.enums.RankingType,
) -> Scores:
    return await get_scores_for(
        beatmap=beatmap,
        game_mode=game_mode,
        ranking_type=ranking_type,
        accepted_scores=accepted_scores,
        mods=None,
    )


async def get_mod_specific_scores_for(
    beatmap: Beatmap,
    game_mode: osuGameMode,
    accepted_scores: AcceptedScores,
    ranking_type: ossapi.enums.RankingType,
    mods: Mods,
) -> Scores:
    return await get_scores_for(
        beatmap=beatmap,
        game_mode=game_mode,
        ranking_type=ranking_type,
        accepted_scores=accepted_scores,
        mods=mods,
    )


async def get_replay(score_id: int, beatmap_md5: str | None = None) -> bytes | None:
    """Returns compatible stable replay frames for the given score ID or None if it doesn't match the conditions"""
    # Check if replay is available for this score & md5's match
    osuApi = await get_ossapi_async()

    try:
        # Full replay payload
        replay_data = await osuApi.download_score(
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
            log.error(
                f"Replay beatmap md5 {replay_beatmap_md5} does not match expected {beatmap_md5}"
            )
            return None
        else:
            return replay_frames

    except ValueError as e:
        log.error(f"Error fetching replay for score {score_id}: {e}")
        raise
