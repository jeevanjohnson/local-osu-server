import socket
import inspect
import asyncio
from typing import Any
from typing import Callable
from typing import Optional
from typing import Coroutine
from server.router import Router
from asyncio import AbstractEventLoop
from server.responses import Response
from server.responses import JsonResponse
from server.responses import ALL_RESPONSES

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

from server import params

def Alias(
    *alias: str
) -> Any:
    return params.Alias(
        *alias
    )

def Query(
    func: Callable,
    alias: Optional[params.Alias] = None
) -> Any: 
    return params.Query(
        func, alias
    )

PARAMS = (params.Query, params.Alias)

class HTTPServer:
    def __init__(
        self, 
        loop: AbstractEventLoop = asyncio.get_event_loop()
    ) -> None:
        self.loop = loop
        self.routers: list[Router] = []
        self.start_method: Optional[Coroutine] = None
        self.shutdown_method: Optional[Coroutine] = None

    def add_router(self, router: Router) -> None:
        self.routers.append(router)

    def parse_args(
        self, 
        args: dict[str, Any],
        func: Callable, 
        request: Optional[Request] = None
    ) -> dict[str, Any]:
        
        signature = inspect.signature(func)

        parsed_args = {}
        if not signature.parameters or not args:
            return parsed_args

        parameter_keys = args.keys()
        for arg_name, func_arg in signature.parameters.items():
            arg_names = [arg_name]
            default_value = func_arg.default

            if isinstance(default_value, Request) and request:
                parsed_args[arg_name] = request
                continue

            is_param = isinstance(default_value, PARAMS)
            if is_param:
                arg_names.extend(default_value.alias)

            parameter_key_check = [key for key in parameter_keys if key in arg_names]
            if not parameter_key_check:
                continue
            
            arg_key, = parameter_key_check
            parameter_value = args[arg_key]

            if is_param:
                parameter_value = default_value(parameter_value)
            
            if not isinstance(parameter_value, func_arg.annotation):
                parameter_value = func_arg.annotation(parameter_value)
            
            parsed_args[arg_name] = parameter_value
        
        return parsed_args

    def starting(self, func: Callable) -> Callable:
        self.start_method = func()
        return func
    
    def shutdown(self, func: Callable) -> Callable:
        self.shutdown_method = func()
        return func

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
            print('you see if u somehow get here, what is wrong with you')
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
        self, client: socket.socket
    ) -> None:
        data = await self.loop.sock_recv(client, 1024)
        if not data:
            await self.loop.sock_sendall(client, b'')
            client.close()
            return
        
        request = self.parse(data)
        if 'content_length' in request:
            length = request.content_length
            if length > 1024:
                data += await self.loop.sock_recv(client, length)
                request = self.parse(data)
        
        for router in self.routers:
            if not (match := router.match(request.path)):
                continue
            
            if isinstance(match, str):
                path = request.path.removeprefix(match)
            else:
                path = request.path.removeprefix(router.main_destination) # type: ignore
            
            for route in router:
                if request.method not in route.methods:
                    continue

                match = route.match(path)
                if match is False:
                    continue
                
                if isinstance(match, dict):
                    request.args = match
                else:
                    request.args = {}

                all_possible_parameters = request.__dict__
                all_possible_parameters |= request.params
                all_possible_parameters |= request.args

                route_handler = route.handler
                resp = await route_handler(**self.parse_args(
                    all_possible_parameters, route_handler, request
                ))

                if isinstance(resp, ALL_RESPONSES):
                    await self.loop.sock_sendall(
                        client, resp.to_bytes()
                    )
                elif isinstance(resp, bytearray):
                    await self.loop.sock_sendall(
                        client, Response(200, bytes(resp)).to_bytes()
                    )
                elif isinstance(resp, str):
                    await self.loop.sock_sendall(
                        client, Response(200, resp.encode()).to_bytes()
                    )
                elif isinstance(resp, bytes):
                    await self.loop.sock_sendall(
                        client, resp
                    )
                else:
                    try:
                        await self.loop.sock_sendall(
                            client, Response(200, bytes(resp)).to_bytes()
                        )
                    except:
                        raise Exception(f'unknown type for resp, type: {type(resp)}')
                
                client.close()
                return

        print(request.path, request.params, request.method)
        await self.loop.sock_sendall(
            client, JsonResponse(404, {'error': 'not found'}).to_bytes()
        )
        client.close()
        return

    async def _run(
        self, 
        bind: tuple[str, int] = ('127.0.0.1', 5000), 
        listening: int = 16,
        background_tasks: Optional[list[Callable]] = None
    ) -> None:
        
        with socket.socket(socket.AF_INET) as sock:
            if self.start_method:
                await self.start_method
            
            if background_tasks:
                [asyncio.create_task(func()) for func in background_tasks]

            # used to avoid 'Address already in use'
            #sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            sock.bind(bind)
            sock.listen(listening)
            sock.setblocking(False)

            print(
                'Server is up and running on {}:{}!'.format(*bind)
            )

            while True:
                client, addr = await self.loop.sock_accept(sock)
                self.loop.create_task(self.handle_con(client))
    
    def run(
        self,
        bind: tuple[str, int] = ('127.0.0.1', 5000), 
        listening: int = 16,
        background_tasks: Optional[list[Callable]] = None
    ) -> None:
        try:
            self.loop.run_until_complete(self._run(
                bind, listening, background_tasks
            ))
        except (KeyboardInterrupt, SystemExit):
            [task.cancel() for task in asyncio.all_tasks()]
            if self.shutdown_method:
                self.loop.run_until_complete(
                    self.shutdown_method
                )
        
        try:
            self.loop.close()
        except:
            pass

        return