from jays_tools.architecture import Repository
from pathlib import Path
from constants import Paths


class ProcessRepository(Repository):
    def __init__(self) -> None:
        self.path = Paths.INTERFACE_PID

    def save_process_id(self, process_id: int) -> None:
        self.path.write_text(str(process_id))

    def get_process_id(self) -> int | None:
        if self.path.exists():
            return int(self.path.read_text())

        return None

    def clear_process_id(self) -> None:
        if self.path.exists():
            self.path.unlink()
