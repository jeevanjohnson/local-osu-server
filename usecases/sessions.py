"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""

import usecases.profiles
from adapters import log, log_time
from constants import SESSIONS_FILE
from models.bancho.scores import Scores, StableScore
from models.database.sessions import CurrentSession as Session
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from osuProtocol.server_packets import (
    ClientRelog,
    Notification,
    PlayerStats,
)
from repositories.sessions import SessionRepository


# @log_time
async def delete_current_session() -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    await sessions_repo.delete_current_session()

    return


# @log_time
async def create_session(profile_name: str) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    await sessions_repo.create_session(profile_name)

    return


# @log_time
async def session_exists() -> bool:
    return await maybe_get_current_session() is not None


# @log_time
async def require_current_session() -> Session:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    return await sessions_repo.require_current_session()


# @log_time
async def maybe_get_current_session() -> Session | None:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    return await sessions_repo.maybe_get_current_session()


@log_time
async def update_current_session(session: Session, update_client: bool = False) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    if update_client:
        try:
            profile = await usecases.profiles.require_profile(session.profile_name)
        except ProfileNotFoundError:
            log.warning(
                "Attempted to update current session but the associated profile was not found."
            )
            return

        ranked_score = profile.performance[session.current_game_mode].ranked_score
        accuracy = profile.performance[session.current_game_mode].accuracy
        play_count = profile.performance[session.current_game_mode].playcount
        total_score = profile.performance[session.current_game_mode].total_score
        rank = profile.performance[session.current_game_mode].rank
        performance_points = profile.performance[
            session.current_game_mode
        ].performance_points

        session.packet_queue += PlayerStats(
            user_id=2,
            action=session.osu_client.status,
            info_text=session.osu_client.status_message,
            beatmap_md5=session.latest_beatmap.md5 if session.latest_beatmap else "",
            mods=session.latest_enabled_mods,
            game_mode=session.current_game_mode,
            beatmap_id=session.latest_beatmap.id if session.latest_beatmap else 0,
            ranked_score=ranked_score,
            accuracy=accuracy,
            play_count=play_count,
            total_score=total_score,
            rank=rank,
            performance_points=performance_points,
        ).build()

    await sessions_repo.update_current_session(session)

    return


@log_time
async def notify_client(
    message: str,
) -> None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        log.warning(
            "Attempted to notify client but no active session was found. Message was: "
            + message
        )
        return

    session.packet_queue += Notification(message).build()

    await update_current_session(session)

    return


@log_time
async def restart_client(message: str | None = None) -> None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        log.warning(
            "Attempted to restart client but no active session was found. Message was: "
            + (message or "None")
        )
        return

    if message is not None:
        session.packet_queue += Notification(message).build()

    session.packet_queue += ClientRelog(millisecond_delay=0).build()

    await update_current_session(session)

    return


@log_time
async def silent_restart_client() -> None:
    await restart_client()


@log_time
async def clear_packet_queue() -> Session | None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        log.warning("Attempted to clear packet queue but no active session was found.")
        return

    session.packet_queue = b""
    await update_current_session(session)

    return session


async def update_avaliable_stable_replay_ids_from_ids(ids: list[int]) -> None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        log.warning(
            "Attempted to update available stable replay IDs but no active session was found."
        )
        return

    assert session.latest_beatmap is not None, (
        "Cannot update available stable replay IDs without a latest beatmap in the session."
    )
    session.latest_beatmap.avaliable_replays = ids
    await update_current_session(session)

    return


async def update_avaliable_stable_replay_ids_from_scores(scores: Scores) -> None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        log.warning(
            "Attempted to update available stable replay IDs but no active session was found."
        )
        return

    if session.latest_beatmap is None:
        log.warning(
            "Cannot update available stable replay IDs without a latest beatmap in the session."
        )
        return

    for score in scores.scores:
        if isinstance(score, StableScore) and score.replay_available:
            session.latest_beatmap.avaliable_replays.append(score.score_id)

    await update_current_session(session)
