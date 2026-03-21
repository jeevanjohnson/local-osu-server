from ossapi import UserCompact

from models.bancho.scores import (
    Combo, Scores, Score, Mods,
    StableScore, LazerScore
)
from osuProtocol.client_web import LeaderboardType, osuMods
from osuProtocol.server_packets import osuGameMode
from usecases.providers import get_ossapi_async
from models.database.beatmaps import (
    CurrentBeatmap as Beatmap,
)
import ossapi.enums

from repositories.profiles import ProfilesRepository
from constants import PROFILES_FILE, SESSIONS_FILE
from repositories.sessions import SessionRepository
from pprint import pprint
from typing import TypedDict, Any

class ScoresResolver:
    ...


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

async def get_scores_for(
    beatmap: Beatmap,
    leaderboard_type: LeaderboardType,
    game_mode: osuGameMode,
    limit: int,
    stable_only: bool,
    mods: osuMods | None = None,
) -> Scores | None:
    lazer_only = False

    profile_repo = ProfilesRepository(PROFILES_FILE)
    session_repo = SessionRepository(SESSIONS_FILE)

    ranking_type = ossapi.enums.RankingType.SCORE

    session = session_repo.get_current_session()
    if session:
        profile = profile_repo.get_profile(session.profile_name)
        if profile:
            ranking_type = profile.settings.scoring_algorithm.to_api_v2()

    osuApi = await get_ossapi_async()

    # TODO: Implement self scores and friends scores leaderboards

    # if score v2, show only lazer scores to kinda match the slider acc lbs.
    # TODO MAKE THIS A CONFIG OPTION. 
    # Some users might want to see score v2 scores on the all mods lb, even if they have score v1 scores.
    if mods and mods & osuMods.SCOREV2:
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

    # print(f"Fetching scores for beatmap {beatmap.id} with mods {mods} and leaderboard type {leaderboard_type.name}...")

    try:
        requested_scores = await osuApi.beatmap_scores(
            beatmap_id=beatmap.id,
            mode=game_mode.to_api_v2(),
            mods=req_mods,
            limit=req_limit,
            legacy_only=stable_only,
            type=ranking_type
        )
    except ValueError as e:
        print(f"Error fetching scores for beatmap {beatmap.id}: {e}")
        return

    if not requested_scores:
        return None
    
    scores = Scores(
        all_scores=[]
    )

    for score in requested_scores.scores:
        user: UserCompact = score._ossapi_data["_user"]

        if score.legacy_score_id and lazer_only:
            continue

        if score.legacy_score_id:
            score_model = StableScore
        else:
            score_model = LazerScore

        score_mods = [] # https://github.com/ppy/osu-web/blob/master/database/mods.json
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
                    pprint(f"Error processing mod settings for mod {mod.acronym}: {e}\nMod settings: {mod.settings}")
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
            combo=Combo(
                actual=score.max_combo,
                max=beatmap.max_combo
            ),
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

    return scores