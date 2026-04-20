import subprocess

from core.repositories.states.interface import InterfaceStateRepository


def shutdown() -> None:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    if database.subprocess_pid is not None:
        print(f"Shutting down interface with PID {database.subprocess_pid}")

        try:
            subprocess.run(
                ["taskkill", "/PID", str(database.subprocess_pid), "/F", "/T"]
            )
        except Exception as e:
            print(f"Error killing process: {e}")

        database.subprocess_pid = None
        state_repo.update_state(database)
    
    print("Interface shutdown complete.")


def set_process_id(pid: int) -> None:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    database.subprocess_pid = pid
    state_repo.update_state(database)
