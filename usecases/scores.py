from typing import TypedDict, TypeAlias, cast
from ossapi import Ossapi, OssapiV1
from ossapi.ossapi import Score as LegacyScore
from ossapi.enums import RankingType, GameMode
from ossapi.models import BeatmapScores
from osuProtocol.server_packets import osuGameMode
from osuProtocol.client_web import LeaderboardType
from osuProtocol.server_packets import osuMods
import usecases.beatmaps
from ossapi import Score
from ossapi import UserCompact

from osuProtocol.client_web import Scores, LazerScore, LegacyScore as ClientLegacyScore

LegacyScores: TypeAlias = list[LegacyScore]

from constants import SERVER_SETTINGS_FILE
from repositories.server_settings import ServerSettingsRepository

CLIENT_MODS_TO_API_V2_MODS = {
    osuGameMode.STANDARD: GameMode.OSU,
    osuGameMode.TAIKO: GameMode.TAIKO,
    osuGameMode.CATCH_THE_BEAT: GameMode.CATCH,
    osuGameMode.MANIA: GameMode.MANIA,
}

class ApiV2CredentialsError(Exception):
    pass

def _is_stable_v2_score(score: Score) -> bool:
    # API v2 exposes `legacy_score_id` for stable-origin plays.
    return score.legacy_score_id is not None

def _mods_from_v2_score(score: Score) -> tuple[osuMods, list[str]]:
    mods = osuMods.NOMOD
    LAZER_MODS = []

    for mod in score.mods:
        acronym = mod.acronym
        try:
            mods |= osuMods.from_mod_string(acronym)
        except ValueError:
            LAZER_MODS.append(acronym)
            print(f"Warning: Unrecognized mod acronym '{acronym}' in score {score.score_id}. This mod will be ignored in the API v1-compatible legacy leaderboard, but should still work correctly in the lazer leaderboard if the client supports it.")

    return mods, LAZER_MODS

def get_ossapi_v1() -> OssapiV1:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = server_settings_repo.get_server_settings()
    if server_settings is None:
        raise ValueError("Server settings not found. This should never happen, please contact the developer.")
    
    if server_settings["osu_api_key_v1"] is None:
        raise ApiV2CredentialsError("osu! API v1 token not found in server settings. Please set it up in the server settings page.")

    osuApiV1 = OssapiV1(server_settings["osu_api_key_v1"])

    return osuApiV1

def get_ossapi() -> Ossapi:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = server_settings_repo.get_server_settings()
    if server_settings is None:
        raise ValueError("Server settings not found. This should never happen, please contact the developer.")
    
    if server_settings["osu_api_v2_client_id"] is None or server_settings["osu_api_v2_client_secret"] is None:
        raise ApiV2CredentialsError("osu! API v2 credentials not found in server settings. Please set them up in the server settings page.")

    try:
        client_id = int(server_settings["osu_api_v2_client_id"])
    except ValueError:
        raise ApiV2CredentialsError("Invalid osu! API v2 client ID in server settings. Please ensure it's a valid integer.")

    client_secret = server_settings["osu_api_v2_client_secret"]

    osuApi = Ossapi(client_id, client_secret)

    return osuApi

def get_scores_for_beatmap_id(
    beatmap_id: int,
    # leaderboard_type: LeaderboardType,
    game_mode: osuGameMode,
    limit: int,
    legacy_leaderboard: bool,
    mods: osuMods | None = None,
) -> Scores | None:
    osuApi = get_ossapi()
    beatmap = usecases.beatmaps.get_beatmap(beatmap_id=beatmap_id)

    if beatmap is None:
        return None

    beatmap_max_combo = beatmap.max_combo or 0

    valid_game_mode = CLIENT_MODS_TO_API_V2_MODS[game_mode]

    try:
        requested_scores = osuApi.beatmap_scores(
            beatmap_id=beatmap_id,
            type=RankingType.SCORE, # TODO: profile config
            mode=valid_game_mode,
            mods=mods,
            limit=limit,
            legacy_only=legacy_leaderboard
        )
    except ValueError:
        return None
    
    if not requested_scores:
        return None
    
    # Convert the requested scores to the appropriate client-side score types
    scores = Scores()
    for score in requested_scores.scores:
        user: UserCompact = score._ossapi_data["_user"]

        if score.id is None:
            print(f"Score {score} has no ID")

        if legacy_leaderboard and _is_stable_v2_score(score):
            legacy_total_score = score.legacy_total_score if score.legacy_total_score > 0 else score.total_score
            scores += ClientLegacyScore(
                score_id=score.legacy_score_id or score.id or 0,
                username=user.username,
                total_score=legacy_total_score,
                max_combo=score.max_combo,
                count50=score.statistics.meh or 0,
                count100=score.statistics.ok or 0,
                count300=score.statistics.great or 0,
                count_miss=score.statistics.miss or 0,
                perfect=score.legacy_perfect,
                enabled_mods=_mods_from_v2_score(score)[0],
                user_id=user.id,
                time_set=int(score.ended_at.timestamp()),
                replay_available=score.has_replay,
                pp=int(score.pp or 0),
                beatmap_max_combo=beatmap_max_combo,
            )
        else:
            scores += LazerScore(
                score_id=score.id or 0,
                username=user.username,
                total_score=score.total_score,
                max_combo=score.max_combo,
                count50=score.statistics.meh or 0,
                count100=score.statistics.ok or 0,
                count300=score.statistics.great or 0,
                count_miss=score.statistics.miss or 0,
                perfect=score.legacy_perfect,
                user_id=user.id,
                time_set=int(score.ended_at.timestamp()),
                replay_available=score.has_replay,
                pp=int(score.pp or 0),
                beatmap_max_combo=beatmap_max_combo,
                enabled_mods=[mod.acronym for mod in score.mods]
            )

    return scores

def get_scores_for_beatmap_md5(
    beatmap_md5: str,
    leaderboard_type: LeaderboardType,
    game_mode: osuGameMode,
    limit: int,
    legacy_leaderboard: bool,
    mods: osuMods | None = None,
) -> Scores | None:
    osuApi = get_ossapi()
    
    beatmap = usecases.beatmaps.get_beatmap(beatmap_md5=beatmap_md5)

    if beatmap is None:
        return None

    beatmap_max_combo = beatmap.max_combo or 0
    
    valid_game_mode = CLIENT_MODS_TO_API_V2_MODS[game_mode]

    try:
        requested_scores = osuApi.beatmap_scores(
            beatmap_id=beatmap.id,
            type=RankingType.SCORE, # TODO: profile config
            mode=valid_game_mode,
            mods=mods,
            limit=limit,
            legacy_only=legacy_leaderboard
        )
    except ValueError:
        return None
    
    if not requested_scores:
        return None
    
    # Convert the requested scores to the appropriate client-side score types
    scores = Scores()
    for score in requested_scores.scores:
        user: UserCompact = score._ossapi_data["_user"]

        if score.id is None:
            print(f"Score {score} has no ID")

        if legacy_leaderboard and _is_stable_v2_score(score):
            legacy_total_score = score.legacy_total_score if score.legacy_total_score > 0 else score.total_score
            scores += ClientLegacyScore(
                score_id=score.legacy_score_id or score.id or 0,
                username=user.username,
                total_score=legacy_total_score,
                max_combo=score.max_combo,
                count50=score.statistics.meh or 0,
                count100=score.statistics.ok or 0,
                count300=score.statistics.great or 0,
                count_miss=score.statistics.miss or 0,
                perfect=score.legacy_perfect,
                enabled_mods=_mods_from_v2_score(score)[0],
                user_id=user.id,
                time_set=int(score.ended_at.timestamp()),
                replay_available=score.has_replay,
                pp=int(score.pp or 0),
                beatmap_max_combo=beatmap_max_combo,
            )
        else:
            scores += LazerScore(
                score_id=score.id or 0,
                username=user.username,
                total_score=score.total_score,
                max_combo=score.max_combo,
                count50=score.statistics.meh or 0,
                count100=score.statistics.ok or 0,
                count300=score.statistics.great or 0,
                count_miss=score.statistics.miss or 0,
                perfect=score.legacy_perfect,
                user_id=user.id,
                time_set=int(score.ended_at.timestamp()),
                replay_available=score.has_replay,
                pp=int(score.pp or 0),
                beatmap_max_combo=beatmap_max_combo,
                enabled_mods=[mod.acronym for mod in score.mods]
            )

    return scores

def get_legacy_scores_for_beatmap_id(
    beatmap_id: int
) -> Scores | None:
    osuApiV1 = get_ossapi_v1()

    beatmap = usecases.beatmaps.get_beatmap(beatmap_id=beatmap_id)

    if beatmap is None:
        return None

    try:
        requested_scores = osuApiV1.get_scores(beatmap_id=beatmap_id)
    except ValueError:
        return None
    
    if requested_scores is None:
        return None

    scores = Scores()
    for score in requested_scores:
        if score.mods is not None:
            if isinstance(score.mods.value, int):
                mods = osuMods(score.mods)
            else:
                print("This shouldn't happen, score.mods should be an int or None")
        else:
            mods = osuMods.NOMOD

        assert score.replay_id is not None
        assert score.score is not None
        assert score.username is not None
        assert score.max_combo is not None
        assert score.count_50 is not None
        assert score.count_100 is not None
        assert score.count_300 is not None
        assert score.count_miss is not None
        assert score.perfect is not None
        assert score.user_id is not None
        assert score.date is not None
        assert score.replay_available is not None
        assert score.pp is not None
        assert beatmap.max_combo is not None

        scores += ClientLegacyScore(
            score_id=score.replay_id, # replay_id = score_id ?
            username=score.username,
            total_score=score.score,
            max_combo=score.max_combo,
            count50=score.count_50,
            count100=score.count_100,
            count300=score.count_300,
            count_miss=score.count_miss,
            perfect=score.perfect,
            enabled_mods=mods,
            user_id=score.user_id,
            time_set=int(score.date.timestamp()),
            replay_available=score.replay_available,
            pp=int(score.pp),
            beatmap_max_combo=beatmap.max_combo
        )
    
    return scores

def get_legacy_scores_for_beatmap_md5(
    beatmap_md5: str
) -> Scores | None:
    osuApiV1 = get_ossapi_v1()

    beatmap = usecases.beatmaps.get_beatmap(beatmap_md5=beatmap_md5)

    if beatmap is None:
        return None
    
    try:
        requested_scores = osuApiV1.get_scores(beatmap_id=beatmap.id)
    except ValueError:
        return None
    
    if requested_scores is None:
        return None
    
    scores = Scores()
    for score in requested_scores:
        
        if score.mods is not None:
            if isinstance(score.mods.value, int):
                mods = osuMods(score.mods.value)
            else:
                print("This shouldn't happen, score.mods should be an int or None")
        else:     
            mods = osuMods.NOMOD

        assert score.replay_id is not None
        assert score.score is not None
        assert score.username is not None
        assert score.max_combo is not None
        assert score.count_50 is not None
        assert score.count_100 is not None
        assert score.count_300 is not None
        assert score.count_miss is not None
        assert score.perfect is not None
        assert score.user_id is not None
        assert score.date is not None
        assert score.replay_available is not None
        assert beatmap.max_combo is not None

        if score.pp is None:
            pp = 0
        else:
            pp = int(score.pp)

        scores += ClientLegacyScore(
            score_id=score.replay_id, # replay_id = score_id ?
            username=score.username,
            total_score=score.score,
            max_combo=score.max_combo,
            count50=score.count_50,
            count100=score.count_100,
            count300=score.count_300,
            count_miss=score.count_miss,
            perfect=score.perfect,
            enabled_mods=mods,
            user_id=score.user_id,
            time_set=int(score.date.timestamp()),
            replay_available=score.replay_available,
            pp=pp,
            beatmap_max_combo=beatmap.max_combo
        )
    
    return scores

def get_legacy_scores_for_beatmap(
    beatmap_md5: str | None = None,
    beatmap_id: int | None = None,
) -> Scores | None:
    if beatmap_md5:
        scores = get_legacy_scores_for_beatmap_md5(beatmap_md5=beatmap_md5)
        if scores:
            return scores
    
    if beatmap_id:
        scores = get_legacy_scores_for_beatmap_id(beatmap_id=beatmap_id)
        if scores:
            return scores
    
    return None

def get_scores_for_beatmap(
    leaderboard_type: LeaderboardType,
    game_mode: osuGameMode,
    limit: int,
    legacy_leaderboard: bool,
    mods: osuMods | None = None,
    beatmap_id: int | None = None,
    beatmap_md5: str | None = None,
) -> Scores | None:
    lazer_scores = _get_scores_for_beatmap(
        leaderboard_type=leaderboard_type,
        game_mode=game_mode,
        limit=limit,
        legacy_leaderboard=legacy_leaderboard,
        mods=mods,
        beatmap_id=beatmap_id,
        beatmap_md5=beatmap_md5
    )

    legacy_scores = get_legacy_scores_for_beatmap(
        beatmap_md5=beatmap_md5,
        beatmap_id=beatmap_id
    )

    scores = Scores()

    if lazer_scores:
        scores.extend(lazer_scores)
    
    if legacy_scores:
        scores.extend(legacy_scores)
    
    return scores

def _get_scores_for_beatmap(
        leaderboard_type: LeaderboardType,
        game_mode: osuGameMode,
        limit: int,
        legacy_leaderboard: bool,
        mods: osuMods | None = None,
        beatmap_id: int | None = None,
        beatmap_md5: str | None = None,
) -> Scores | None:
    osuApi = get_ossapi()

    if leaderboard_type != LeaderboardType.MODS:
        mods = None

    # TODO: support country?

    if beatmap_id is not None:
        scores = get_scores_for_beatmap_id(
            beatmap_id=beatmap_id,
            game_mode=game_mode,
            mods=mods,
            limit=limit,
            legacy_leaderboard=legacy_leaderboard
        )
        if scores:
            return scores
    
    if beatmap_md5 is not None:
        scores = get_scores_for_beatmap_md5(
            beatmap_md5=beatmap_md5,
            leaderboard_type=leaderboard_type,
            game_mode=game_mode,
            mods=mods,
            limit=limit,
            legacy_leaderboard=legacy_leaderboard
        )
        if scores:
            return scores
    
    return None

    


    