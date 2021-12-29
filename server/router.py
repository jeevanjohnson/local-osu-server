import re
from typing import Any
from typing import Union
from typing import Iterator
from typing import Callable
from typing import Coroutine
from server.responses import All_Responses

responses = Union[bytearray, bytes, str, All_Responses]

HANDLER = Callable[..., Coroutine[Any, Any, responses]]

class Route:
    def __init__(
        self, path: Union[str, re.Pattern],
        methods: list[str],
        handler: HANDLER,
        origin: 'Router'
    ) -> None:
        self.path = path
        self.methods = methods
        self.handler = handler
        self.origin = origin
    
    def match(self, request_path: str) -> Union[bool, dict[str, str]]:
        if isinstance(self.path, str):
            return self.path == request_path
        
        match = self.path.match(request_path)
        if not match:
            return False
        
        return match.groupdict()

class Router:
    def __init__(
        self, main_destination: Union[str, tuple[str]]
    ) -> None:
        if isinstance(main_destination, tuple):
            main_destination = tuple(sorted( # type: ignore
                main_destination, key = len, reverse = True
            ))

        self.main_destination = main_destination
        self.routes: list[Route] = []
    
    def match(self, request_path: str) -> Union[bool, str]:
        if isinstance(self.main_destination, str):
            return request_path.startswith(self.main_destination)
        
        for des in self.main_destination:
            if request_path.startswith(des):
                return des
        
        return False

    def get(self, path: Union[str, re.Pattern]) -> Callable:
        def inner(func: HANDLER) -> Callable:
            self.routes.append(Route(
                path = path, 
                methods = ['GET'], 
                handler = func,
                origin = self
            ))
            return func
        return inner

    def __iter__(self) -> Iterator[Route]:
        return iter(self.routes)
    
    def __repr__(self) -> str:
        return str(self.main_destination)