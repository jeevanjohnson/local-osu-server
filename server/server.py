import re
import http
import socket
import orjson
import asyncio
from typing import Any
from typing import Union
from pathlib import Path
from typing import Callable
from typing import Optional
from typing import TypedDict

# https://datatracker.ietf.org/doc/html/rfc7231#section-6s
HTTP_STATUS_CODES = {
	# {418: "I'm a Teapot"}
	status.value: status.phrase
	for status in http.HTTPStatus
}

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
        self.host: str
    
    def __contains__(self, item: Any) -> bool:
        return self.__dict__.__contains__(item)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Request':
        req = cls()
        req.__dict__.update(data)
        return req
    
    def __repr__(self) -> str:
        return self.path
    
    @property
    def as_url(self) -> str:
        if (
            ':' in self.host or
            self.host == 'localhost'
        ):
            url = f'http://{self.host}{self.path}'
        else:
            url = f'https://{self.host}{self.path}'
        
        params_str = '&'.join([
            f'{k}={v}' for k, v in self.params.items()
        ])

        if params_str:
            return f'{url}?{params_str}'
        else:
            return url
        
class Route(TypedDict):
    path: Union[str, re.Pattern]
    methods: list[str]
    func: Callable

class Response:
    def __init__(
        self, code: int, body: Union[str, bytes, bytearray], 
        headers: dict[str, Any] = {}
    ) -> None:
        self.code = code
        self.body = body
        self.headers = headers

    def to_bytes(self) -> bytes:
        if isinstance(self.body, str):
            self.body = self.body.encode()
              
        resp = bytearray((
            f'HTTP/1.1 {self.code} {HTTP_STATUS_CODES[self.code]}\r\n'
            f'Content-Length: {len(self.body)}\r\n'
        ).encode())

        for key, value in self.headers.items():
            resp += f'{key}: {value}\r\n'.encode()

        resp += b'\r\n'
        
        return bytes(resp + self.body)
    
class HTMLResponse(Response):
    def __init__(self, path: Union[str, Path], **kwargs) -> None:
        if isinstance(path, Path):
            content = path.read_text()
        else:
            content = Path(path).read_text()
        
        try:
            super().__init__(
                code = 200, 
                body = content.format(**kwargs),
                headers = {'Content-type': 'text/html'}
            )
        except:
            super().__init__(
                code = 200, 
                body = content,
                headers = {'Content-type': 'text/html'}
            )

class ImageResponse(Response):
    def __init__(
        self, image_bytes: Union[bytes, bytearray],
        image_extenton: str = 'jpeg'
    ) -> None:
        image_extenton = image_extenton.replace('.', '', 1)
        super().__init__(
            code = 200,
            body = image_bytes,
            headers = {'Content-type': f'image/{image_extenton}'}
        )

class JsonResponse(Response):
    def __init__(self, code: int, json: dict) -> None:
        super().__init__(
            code = code,
            body = orjson.dumps(json),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

class SuccessJsonResponse(JsonResponse):
    def __init__(self, json: dict) -> None:
        super().__init__(200, json)

ALL_RESPONSES = (
    Response, HTMLResponse, 
    ImageResponse, JsonResponse,
    SuccessJsonResponse
)    

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

            if isinstance(resp, ALL_RESPONSES):
                await loop.sock_sendall(client, resp.to_bytes())
            elif isinstance(resp, bytearray):
                await loop.sock_sendall(client, bytes(resp))
            elif isinstance(resp, str):
                await loop.sock_sendall(
                    client, Response(200, resp.encode()).to_bytes()
                )
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
        shutdown_method: Optional[Callable],
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

            print(
                f'Server is up and running on port {bind[1]}!'
            )
            try:
                while True:
                    client, addr = await loop.sock_accept(sock)
                    loop.create_task(self.handle_con(client, loop))
            except (KeyboardInterrupt, SystemExit):
                if shutdown_method:
                    await shutdown_method()
                
                return

    def run(
        self, bind: tuple[str, int], 
        listening: int = 5, 
        before_startup: Optional[Callable] = None,
        shutdown_method: Optional[Callable] = None,
        background_tasks: Optional[list[Callable]] = None
    ) -> None:
        asyncio.run(self._run(
            bind = bind,
            listening = listening,
            before_startup = before_startup,
            shutdown_method = shutdown_method,
            background_tasks = background_tasks
        ))