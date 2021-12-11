import os
from pathlib import PosixPath
from pathlib import WindowsPath

if os.name == 'nt':
    base = WindowsPath
else:
    base = PosixPath

class File(base): # type: ignore
    def __init__(self, path: str) -> None:
        self._cached_stamp = None
        
        super().__new__(base, path)
        self.is_changed()
    
    def is_changed(self) -> bool:
        stamp = self.stat().st_mtime

        if self._cached_stamp is None:
            self._cached_stamp = stamp
            return False

        if stamp != self._cached_stamp:
            self._cached_stamp = stamp
            return True
        else:
            return False
