"""
Purpose/Domain/Concept:
- This file contains the logic related to sessions.
"""

import os
from pathlib import Path

import psutil

import usecases.profiles
from constants import SERVER_SETTINGS_FILE, SESSIONS_FILE
from models.database.sessions import CurrentSession as Session
from osuProtocol.server_packets import (
    Packet,
    Packets,
    PlayerStats,
    Notification,
)
from repositories.server_settings import ServerSettingsRepository
from repositories.sessions import SessionRepository


def delete_current_session() -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    sessions_repo.delete_current_session()

    return


def create_session(profile_name: str) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    sessions_repo.create_session(profile_name)

    return


def session_exists() -> bool:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    session = sessions_repo.get_current_session()

    if session is None:
        return False

    return True


def get_current_session() -> Session | None:
    sessions_repo = SessionRepository(SESSIONS_FILE)
    session = sessions_repo.get_current_session()

    if session is None:
        print("Attempted to retrieve current session but no active session was found.")
        return None

    return session


def update_current_session(session: Session, update_client: bool = False) -> None:
    sessions_repo = SessionRepository(SESSIONS_FILE)

    if update_client:
        profile = usecases.profiles.get_profile(session.profile_name)
        if profile is None:
            print(
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

    # Catch error when no session exists
    sessions_repo.update_current_session(session)

    return

def notify_client(
    message: str,
) -> None:
    session = get_current_session()
    if session is None:
        print(
            "Attempted to notify client but no active session was found. Message was: "
            + message
        )
        return

    session.packet_queue += Notification(message).build()

    update_current_session(session)

    return

# TODO: Log decorator that catches and logs errors and neatly formats them with json so when dev ask
# for logs its easily readable and replicatable.
# TODO: log parameter being "handled_errors" that is a list of error types that are expected and handled so they dont get logged as errors
#             but rather warnings or info depending on the severity of the error.
# (for example, if a session is not found when trying to update it, that is an expected error that can happen when the server receives a request from the client before the user has logged in through the GUI, so it should be handled and logged as a warning rather than an error.)
# TODO: idk if i need this anymore
def enqueue_packets_to_current_session(packets: Packets | Packet) -> Session | None:
    session = get_current_session()

    if session is None:
        print("Attempted to enqueue packets but no active session was found.")
        return

    session.packet_queue += packets.build()

    update_current_session(session)

    return session


def clear_packet_queue() -> Session | None:
    session = get_current_session()
    if session is None:
        print("Attempted to clear packet queue but no active session was found.")
        return

    session.packet_queue = b""
    update_current_session(session)

    return session


# def update_in_game_stats() -> None:
#     session = get_current_session()
#     if session is None:
#         print("Attempted to update stats but no active session was found.")
#         return # TODO: Raise Error

#     profile = usecases.profiles.get_profile(session.profile_name)
#     if profile is None:
#         print("Attempted to update stats but the associated profile was not found.")
#         return

#     ranked_score = profile.performance[session.current_game_mode].ranked_score
#     accuracy = profile.performance[session.current_game_mode].accuracy
#     play_count = profile.performance[session.current_game_mode].playcount
#     total_score = profile.performance[session.current_game_mode].total_score
#     rank = profile.performance[session.current_game_mode].rank
#     performance_points = profile.performance[session.current_game_mode].performance_points

#     if session.latest_beatmap:
#         md5 = session.latest_beatmap.md5
#         bmap_id = session.latest_beatmap.id
#     else:
#         md5 = ""
#         bmap_id = 0

#     enqueue_packets_to_current_session(
#         PlayerStats(
#             user_id=2,
#             action=session.osu_client.status,
#             info_text=session.osu_client.status_message,
#             beatmap_md5=md5,
#             mods=session.latest_enabled_mods,
#             game_mode=session.current_game_mode,
#             beatmap_id=bmap_id,
#             ranked_score=ranked_score,
#             accuracy=accuracy,
#             play_count=play_count,
#             total_score=total_score,
#             rank=rank,
#             performance_points=performance_points
#         )
#     )

#     return


def retrieve_songs_folder() -> Path | None:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    settings = server_settings_repo.get_server_settings()

    if settings.osu_songs_folder_override:
        return settings.osu_songs_folder_override

    processes = [
        process for process in psutil.process_iter() if process.name() == "osu!.exe"
    ]

    if not processes:
        print("Attempted to retrieve songs folder but osu! process was not found.")
        return None  # raise error that osu! process was not found, cannot retrieve songs folder

    osu_path = Path(processes[0].exe())

    cfg_path: Path | None = None
    for cfg_file in osu_path.parent.glob("osu!.*.cfg"):
        if cfg_file.is_file():
            cfg_path = cfg_file
            break

    if cfg_path is None:
        print("Attempted to retrieve songs folder but osu! cfg file was not found.")
        return None  # raise error that osu! cfg file was not found, cannot retrieve songs folder

    raw_cfg = cfg_path.read_text(errors="ignore")
    songs_folder: str | None = None
    for line in raw_cfg.splitlines():
        line = line.strip()

        if line.startswith("BeatmapDirectory"):
            songs_folder = line.split("=")[1].strip()
            break

    if songs_folder is None:
        print(
            "Attempted to retrieve songs folder but songs folder path was not found in osu! cfg file."
        )
        return None  # raise error that songs folder path was not found in cfg file, cannot retrieve songs folder

    if os.path.isabs(songs_folder):
        return Path(songs_folder)
    else:
        return osu_path.parent / songs_folder


def retrieve_replays_folder() -> Path | None:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    settings = server_settings_repo.get_server_settings()

    if settings.osu_replay_folder_override:
        return settings.osu_replay_folder_override

    processes = [
        process for process in psutil.process_iter() if process.name() == "osu!.exe"
    ]

    if not processes:
        print("Attempted to retrieve replays folder but osu! process was not found.")
        return None  # raise error that osu! process was not found, cannot retrieve replays folder

    osu_path = Path(processes[0].exe())
    return osu_path.parent / "Replays"
