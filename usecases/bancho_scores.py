import asyncio
import time
from typing import Any

import ossapi.enums
from ossapi import UserCompact

from adapters.app_logger import app_logger
from constants import PROFILES_FILE, SESSIONS_FILE
from models.bancho.scores import Combo, LazerScore, Mods, Scores, StableScore
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from models.domain.gameplay import osuGameMode, osuMods
from osuProtocol.client_web import LeaderboardType
from repositories.profiles import ProfilesRepository
from repositories.sessions import SessionRepository
from usecases.providers import get_ossapi_async

_SCORE_HOT_CACHE_TTL_SECONDS = 300
_SCORE_HOT_CACHE_MAX_SIZE = 1024
_score_hot_cache: dict[tuple[Any, ...], tuple[float, Scores]] = {}
_score_inflight_requests: dict[tuple[Any, ...], asyncio.Task[Scores | None]] = {}


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


def _get_cached_scores(cache_key: tuple[Any, ...]) -> Scores | None:
    cached = _score_hot_cache.get(cache_key)
    if cached is None:
        return None

    cached_at, cached_scores = cached
    if time.monotonic() - cached_at > _SCORE_HOT_CACHE_TTL_SECONDS:
        _score_hot_cache.pop(cache_key, None)
        return None

    return cached_scores


def _cache_scores(cache_key: tuple[Any, ...], scores: Scores) -> None:
    if cache_key in _score_hot_cache:
        _score_hot_cache.pop(cache_key, None)

    if len(_score_hot_cache) >= _SCORE_HOT_CACHE_MAX_SIZE:
        oldest_key = next(iter(_score_hot_cache))
        _score_hot_cache.pop(oldest_key, None)

    _score_hot_cache[cache_key] = (time.monotonic(), scores)


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


@app_logger.log(msg="usecase get scores for beatmap")
async def get_scores_for(
    beatmap: Beatmap,
    leaderboard_type: LeaderboardType,
    game_mode: osuGameMode,
    limit: int,
    stable_only: bool,
    mods: osuMods | None = None,
) -> Scores | None:
    show_lazer_only_if_score_v2 = False
    lazer_only = False

    profile_repo = ProfilesRepository(PROFILES_FILE)
    session_repo = SessionRepository(SESSIONS_FILE)

    ranking_type = ossapi.enums.RankingType.SCORE

    try:
        session = await session_repo.require_current_session()
        profile = await profile_repo.require_profile(session.profile_name)
        ranking_type = profile.settings.scoring_algorithm.to_api_v2()
        show_lazer_only_if_score_v2 = (
            profile.settings.score_v2_shows_lazer_only_leaderboard
        )
    except (SessionNotFoundError, ProfileNotFoundError):
        pass

    osuApi = await get_ossapi_async()

    # TODO: Implement self scores and friends scores leaderboards

    # if score v2, show only lazer scores to kinda match the slider acc lbs.
    # Some users might want to see score v2 scores on the all mods lb, even if they have score v1 scores.
    if mods and mods & osuMods.SCOREV2 and show_lazer_only_if_score_v2:
        mods &= ~osuMods.SCOREV2
        lazer_only = True
        # Override limit to fetch more scores in case there is more lazer
        limit = 100

    if leaderboard_type == LeaderboardType.MODS and mods is not None:
        req_mods = int(mods)
        req_limit = limit
    else:
        req_mods = None
        req_limit = limit

    cache_key = _make_score_cache_key(
        beatmap_id=beatmap.id,
        game_mode=game_mode,
        leaderboard_type=leaderboard_type,
        stable_only=stable_only,
        ranking_type=ranking_type,
        req_mods=req_mods,
        req_limit=req_limit,
        lazer_only=lazer_only,
    )

    cached_scores = _get_cached_scores(cache_key)
    if cached_scores is not None:
        return cached_scores

    inflight_request = _score_inflight_requests.get(cache_key)
    if inflight_request is not None:
        return await asyncio.shield(inflight_request)

    async def _resolve_scores() -> Scores | None:
        app_logger.warning(
            f"Fetching scores for beatmap {beatmap.id} with mods {mods} and leaderboard type {leaderboard_type.name}..."
        )

        try:
            requested_scores = await osuApi.beatmap_scores(
                beatmap_id=beatmap.id,
                mode=game_mode.to_api_v2(),
                mods=req_mods,
                limit=req_limit,
                legacy_only=stable_only,
                type=ranking_type,
            )
        except ValueError as e:
            app_logger.error(f"Error fetching scores for beatmap {beatmap.id}: {e}")
            return None

        if not requested_scores:
            return None

        scores = Scores(all_scores=[])

        for score in requested_scores.scores:
            user: UserCompact = score._ossapi_data["_user"]

            if score.legacy_score_id and lazer_only:
                continue

            if score.legacy_score_id:
                score_model = StableScore
            else:
                score_model = LazerScore

            score_mods = []  # https://github.com/ppy/osu-web/blob/master/database/mods.json
            for mod in score.mods:
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
                        app_logger.warning(
                            f"Error processing mod settings for mod {mod.acronym}: {e}\nMod settings: {mod.settings}"
                        )
                else:
                    score_mods.append(mod.acronym)

            perfect = bool(score.is_perfect_combo)

            if score.pp is None:
                pp = 0
            else:
                pp = int(score.pp)

            parsed_score = score_model(
                score_id=score.id or 0,
                username=user.username,
                total_score_value=score.total_score,
                combo=Combo(actual=score.max_combo, max=beatmap.max_combo),
                count50=score.statistics.meh or 0,
                count100=score.statistics.ok or 0,
                count300=score.statistics.great or 0,
                count_miss=score.statistics.miss or 0,
                perfect=perfect,
                enabled_mods=Mods(score_mods),
                user_id=user.id,
                time_set=int(score.ended_at.timestamp()),
                replay_available=score.has_replay,
                performance_points=pp,
                game_mode=game_mode,
            )

            scores.all_scores.append(parsed_score)

        _cache_scores(cache_key, scores)

        return scores

    inflight_task: asyncio.Task[Scores | None] = asyncio.create_task(_resolve_scores())
    _score_inflight_requests[cache_key] = inflight_task

    try:
        return await asyncio.shield(inflight_task)
    finally:
        if _score_inflight_requests.get(cache_key) is inflight_task:
            _score_inflight_requests.pop(cache_key, None)
