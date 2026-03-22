"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""

import os
from pathlib import Path

import psutil

import usecases.profiles
from adapters.app_logger import app_logger
from constants import SERVER_SETTINGS_FILE, SESSIONS_FILE
from models.database.sessions import CurrentSession as Session
from models.domain.errors import ProfileNotFoundError, SessionNotFoundError
from osuProtocol.server_packets import (
    ClientRelog,
    Notification,
    PlayerStats,
)
from repositories.server_settings import ServerSettingsRepository
from repositories.sessions import SessionRepository


@app_logger.log(msg="usecase delete current session")
async def delete_current_session() -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    await sessions_repo.delete_current_session()

    return


@app_logger.log(msg="usecase create session")
async def create_session(profile_name: str) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    await sessions_repo.create_session(profile_name)

    return


@app_logger.log(msg="usecase check session exists")
async def session_exists() -> bool:
    return await maybe_get_current_session() is not None


@app_logger.log(msg="usecase require current session")
async def require_current_session() -> Session:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    return await sessions_repo.require_current_session()


@app_logger.log(msg="usecase maybe get current session")
async def maybe_get_current_session() -> Session | None:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    return await sessions_repo.maybe_get_current_session()


@app_logger.log(msg="usecase update current session")
async def update_current_session(session: Session, update_client: bool = False) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    if update_client:
        try:
            profile = await usecases.profiles.require_profile(session.profile_name)
        except ProfileNotFoundError:
            app_logger.warning(
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


@app_logger.log(msg="usecase notify client")
async def notify_client(
    message: str,
) -> None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        app_logger.warning(
            "Attempted to notify client but no active session was found. Message was: "
            + message
        )
        return

    session.packet_queue += Notification(message).build()

    await update_current_session(session)

    return


async def kick_client(message: str) -> None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        app_logger.warning(
            "Attempted to kick client but no active session was found. Message was: "
            + message
        )
        return

    session.packet_queue += Notification(message).build()
    session.packet_queue += ClientRelog(millisecond_delay=500).build()

    await update_current_session(session)

    return


@app_logger.log(msg="usecase restart client")
async def restart_client(message: str | None = None) -> None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        app_logger.warning(
            "Attempted to restart client but no active session was found. Message was: "
            + (message or "None")
        )
        return

    if message is not None:
        session.packet_queue += Notification(message).build()

    session.packet_queue += ClientRelog(millisecond_delay=0).build()

    await update_current_session(session)

    return


@app_logger.log(msg="usecase silent restart client")
async def silent_restart_client() -> None:
    await restart_client()


@app_logger.log(msg="usecase clear packet queue")
async def clear_packet_queue() -> Session | None:
    try:
        session = await require_current_session()
    except SessionNotFoundError:
        app_logger.warning(
            "Attempted to clear packet queue but no active session was found."
        )
        return

    session.packet_queue = b""
    await update_current_session(session)

    return session


@app_logger.log(msg="usecase retrieve songs folder")
async def retrieve_songs_folder() -> Path | None:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    settings = await server_settings_repo.get_server_settings()

    if settings.osu_songs_folder_override:
        return settings.osu_songs_folder_override

    processes = [
        process for process in psutil.process_iter() if process.name() == "osu!.exe"
    ]

    if not processes:
        app_logger.warning(
            "Attempted to retrieve songs folder but osu! process was not found."
        )
        return None  # raise error that osu! process was not found, cannot retrieve songs folder

    osu_path = Path(processes[0].exe())

    cfg_path: Path | None = None
    for cfg_file in osu_path.parent.glob("osu!.*.cfg"):
        if cfg_file.is_file():
            cfg_path = cfg_file
            break

    if cfg_path is None:
        app_logger.warning(
            "Attempted to retrieve songs folder but osu! cfg file was not found."
        )
        return None  # raise error that osu! cfg file was not found, cannot retrieve songs folder

    raw_cfg = cfg_path.read_text(errors="ignore")
    songs_folder: str | None = None
    for line in raw_cfg.splitlines():
        line = line.strip()

        if line.startswith("BeatmapDirectory"):
            songs_folder = line.split("=")[1].strip()
            break

    if songs_folder is None:
        app_logger.warning(
            "Attempted to retrieve songs folder but songs folder path was not found in osu! cfg file."
        )
        return None  # raise error that songs folder path was not found in cfg file, cannot retrieve songs folder

    if os.path.isabs(songs_folder):
        return Path(songs_folder)
    else:
        return osu_path.parent / songs_folder


@app_logger.log(msg="usecase retrieve replays folder")
async def retrieve_replays_folder() -> Path | None:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    settings = await server_settings_repo.get_server_settings()

    if settings.osu_replay_folder_override:
        return settings.osu_replay_folder_override

    processes = [
        process for process in psutil.process_iter() if process.name() == "osu!.exe"
    ]

    if not processes:
        app_logger.warning(
            "Attempted to retrieve replays folder but osu! process was not found."
        )
        return None  # raise error that osu! process was not found, cannot retrieve replays folder

    osu_path = Path(processes[0].exe())
    return osu_path.parent / "Replays"
