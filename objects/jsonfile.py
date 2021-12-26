import orjson
from typing import Any
from pathlib import Path
from typing import Union
from collections import UserDict

class JsonFile(UserDict):
    def __init__(self, path: Union[str, Path]) -> None:
        self._cached_stamp = None

        if isinstance(path, str):
            self.path = Path(path)
        else:
            self.path = path

        if not self.path.exists():
            self.path.write_bytes(b"{}")
            super().__init__()
        else:
            data = orjson.loads(self.path.read_bytes() or b"{}")
            super().__init__(**data)

        self.is_changed()

    def __getitem__(self, key: Any) -> Any:
        return self.data[key]

    def update_file(self) -> None:
        self.path.write_bytes(orjson.dumps(dict(self)))

    def read_file(self) -> None:
        self.data = orjson.loads(self.path.read_bytes())

    def is_changed(self) -> bool:
        stamp = self.path.stat().st_mtime

        if self._cached_stamp is None:
            self._cached_stamp = stamp
            return False

        if stamp != self._cached_stamp:
            self._cached_stamp = stamp
            return True
        else:
            return False