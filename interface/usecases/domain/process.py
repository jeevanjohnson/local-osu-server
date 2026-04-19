import os
import signal

from interface.repositories.interface_state import StateRepository


def shutdown() -> None:
    state_repo = StateRepository()
    database = state_repo.get_state()

    if database.subprocess_pid is not None:
        print(f"Shutting down interface with PID {database.subprocess_pid}")

        try:
            os.kill(database.subprocess_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        database.subprocess_pid = None
        state_repo.update_state(database)


def set_process_id(pid: int) -> None:
    state_repo = StateRepository()
    database = state_repo.get_state()

    database.subprocess_pid = pid
    state_repo.update_state(database)
