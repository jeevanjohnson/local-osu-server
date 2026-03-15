from pathlib import Path
from typing import TypeVar, Generic
import json
from types import TracebackType
from typing import Type
from typing import cast
import time
import asyncio

T = TypeVar("T")

class JsonFile(Generic[T]):
    def __init__(
            self, 
            path: Path | str, 
            generate_backups: bool = False
        ):
        if isinstance(path, str):
            if not path.endswith(".json"):
                path += ".json"
            
            self.path = Path(path)
        else:
            self.path = path
        
        self.db: T | None = None
        self.generate_backups = generate_backups
        self.lock = asyncio.Lock()

    async def __aenter__(self) -> T:
        await self.lock.acquire()

        if self.generate_backups:
            self.backup()

        self.db = self.read()        
        return self.db

    async def __aexit__(
            self, 
            exc_type: Type[BaseException] | None, 
            exc: BaseException | None, 
            tb: TracebackType | None
        ) -> None:
        try:
            if self.db is not None:
                self.write(self.db)
        finally:
            self.lock.release()

    def write(self, data: T) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(str(self.path.absolute()), "w+") as f:
            f.write(
                json.dumps(data, indent=4)
            )
        
        return None

    def read(self) -> T:
        if not self.path.exists():
            return cast(T, {})

        with open(str(self.path.absolute()), "r") as f:
            data = f.read()

        if data:
            return json.loads(data)
        else:
            return cast(T, {})
    
    def backup(self) -> None:
        path_name = f"{self.path.stem}_backup{time.time()}.json"
        path = self.path.parent / path_name

        backup = JsonFile[T](path)
        backup.write(self.read())

        del backup

        return None

    def __enter__(self) -> T:
        if self.generate_backups:
            self.backup()

        self.db = self.read()        
        return self.db
    
    def __exit__(
            self, 
            exc_type: Type[BaseException] | None, 
            exc: BaseException | None, 
            tb: TracebackType | None
        ) -> None:
        if self.db is not None:
            self.write(self.db)