import json
import time
from typing import Any
from pathlib import Path
from typing import Union
from collections import UserDict

class JsonFile(UserDict):
    def __init__(self, path: Union[str, Path]) -> None:
        if isinstance(path, str):
            self.path = Path(path)
        else:
            self.path = path

        if not self.path.exists():
            self.path.write_bytes(b"{}")
            super().__new__(UserDict)
        else:
            data = json.loads(self.path.read_bytes() or b"{}")
            super().__init__(**data)

    def __getitem__(self, key: Any) -> Any:        
        return self.data[key]

    def update_file(self) -> None:
        self.path.write_text(json.dumps(dict(self), indent=len(self)))