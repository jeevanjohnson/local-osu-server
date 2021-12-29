from typing import Any
from typing import Callable
from typing import Optional
from typing import Iterator

class Alias:
    def __init__(
        self, *alias: str
    ) -> None:

        self.alias = list(alias)

    def __iter__(self) -> Iterator:
        return iter(self.alias)
    
    def __call__(self, value: Any) -> Any:
        return value

class Query:
    def __init__(
        self, func: Callable, 
        alias: Optional[Alias] = None
    ) -> None:

        self.query = func

        if alias:
            self.alias: list[str] = list(alias)
        else:
            self.alias: list[str] = []
    
    def __call__(self, value: Any) -> Any:
        return self.query(value)