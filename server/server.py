import re
import socket
import asyncio
from typing import Any
from typing import Union
from typing import Callable
from typing import Optional
from typing import TypedDict
from WebLamp.utils import http_status_codes

# TODO: define more types?
class Request:
    def __init__(self) -> None:
        self.content_length: int
        self.method: str
        self.path: str
        self.params: dict[str, Any]
        self.http_version: float
        self.content_type: str
        self.raw_body: bytes
        self.boundary: str
        self.multipart: Optional[dict[str, Any]]
        self.args: dict[str, Any]
    
    def __contains__(self, item: Any) -> bool:
        return self.__dict__.__contains__(item)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Request':
        req = cls()
        req.__dict__.update(data)
        return req
    
    def __repr__(self) -> str:
        return self.path

class Route(TypedDict):
    path: Union[str, re.Pattern]
    methods: list[str]
    func: Callable

class Response:
    def __init__(
        self, code: int, body: Union[bytes, bytearray], 
        headers: dict[str, Any] = {}
    ) -> None:
        self.code = code
        self.body = body
        self.headers = headers

    def to_bytes(self) -> bytes:        
        resp = bytearray((
            f'HTTP/1.1 {self.code} {http_status_codes[self.code]}\r\n'
            f'Content-Length: {len(self.body)}\r\n'
        ).encode())

        for key, value in self.headers.items():
            resp += f'{key}: {value}\r\n'.encode()

        resp += b'\r\n'
        
        return bytes(resp + self.body)

class Server:
    def __init__(self) -> None:
        self.routes: list[Route] = []
    
    def get(self, path: Union[str, re.Pattern]) -> Callable:
        def inner(func: Callable) -> Callable:
            self.routes.append({
                'path': path,
                'methods': ['GET'],
                'func': func
            })
            return func
        return inner

    def real_type(self, value: str) -> Any:
        if value.replace('-', '', 1).isdecimal():
            return int(value)
        
        try: return float(value)
        except: pass

        return value

    def parse_path(self, path: str) -> tuple[str, dict[str, Any]]:
        params = {}
        if '?' in path:
            split = path.split('?', 1)
            if len(split) == 2:
                path, _params = split
                for param in _params.split('&'):
                    if '=' not in param:
                        continue
                    
                    k, v = param.split('=', 1)
                    params[k] = self.real_type(v)
        
        return (path, params)

    def parse_headers(self, encoded_headers: bytes) -> dict[str, Any]:
        headers = {}
        for idx, header in enumerate(encoded_headers.decode().splitlines()):
            if idx == 0:
                m, p, v = header.split()
                headers['method'] = m
                headers['path'], headers['params'] = self.parse_path(p)
                headers['http_version'] = float(v.replace('HTTP/', ''))
                continue
            
            k, v = header.split(': ', 1)
            headers[k.lower().replace('-', '_')] = self.real_type(v)
    
        return headers

    def parse_body(self, request: Request, body: bytes) -> Request:
        if (
            'content_type' in request and
            request.method == 'POST'
        ):
            request.boundary = '--' + request.content_type.split('; boundary=', 1)[1]
            request.multipart = None
            breakpoint() # TODO: multipart
        else:
            request.raw_body = body
        
        return request

    def parse(self, content: bytes) -> Request:
        request = {}
        split = content.split(b'\r\n\r\n', 1)
        len_split = len(split)

        if len_split == 0:
            return Request()
        if len_split == 1:
            request |= self.parse_headers(split[0])
            return Request.from_dict(request)
        
        headers, body = split
        request |= self.parse_headers(headers)
        request = self.parse_body(Request.from_dict(request), body)

        return request

    async def handle_con(
        self, client: socket.socket,
        loop: asyncio.AbstractEventLoop
    ) -> None:
        data = await loop.sock_recv(client, 1024)
        if not data:
            await loop.sock_sendall(client, b'')
            client.close()
            return
        
        request = self.parse(data)
        if 'content_length' in request:
            length = request.content_length
            if length > 1024:
                data += await loop.sock_recv(client, length)
                request = self.parse(data)
        
        for route in self.routes:
            if request.method not in route['methods']:
                continue

            path = route['path']
            if isinstance(path, str):
                if request.path != path:
                    continue
            else:
                result = path.match(request.path)
                if not result:
                    continue
                
                request.args = result.groupdict()

            resp = await route['func'](request)

            if isinstance(resp, Response):
                await loop.sock_sendall(client, resp.to_bytes())
            elif isinstance(resp, bytearray):
                await loop.sock_sendall(client, bytes(resp))
            elif isinstance(resp, bytes):
                await loop.sock_sendall(client, resp)
            else:
                raise Exception(f'unknown type for resp, type: {type(resp)}')
            
            client.close()
            return

        print(request.path, request.params, request.method)

    async def _run(
        self, bind: tuple[str, int], 
        listening: int, 
        before_startup: Optional[Callable],
        background_tasks: Optional[list[Callable]]
    ) -> None:
        
        with socket.socket(socket.AF_INET) as sock:
            loop = asyncio.get_running_loop()

            if before_startup:
                await before_startup()
            
            if background_tasks:
                [asyncio.create_task(func()) for func in background_tasks]

            sock.bind(bind)
            sock.listen(listening)
            sock.setblocking(False)

            print('server is running!')

            try:
                while True:
                    client, addr = await loop.sock_accept(sock)
                    loop.create_task(self.handle_con(client, loop))
            except KeyboardInterrupt:
                return

    def run(
        self, bind: tuple[str, int], 
        listening: int = 5, 
        before_startup: Optional[Callable] = None,
        background_tasks: Optional[list[Callable]] = None
    ) -> None:
        asyncio.run(self._run(
            bind = bind,
            listening = listening,
            before_startup = before_startup,
            background_tasks = background_tasks
        ))