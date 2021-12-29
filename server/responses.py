import http
import orjson
from typing import Any
from typing import Union
from pathlib import Path

# https://datatracker.ietf.org/doc/html/rfc7231#section-6s
HTTP_STATUS_CODES = {
	# {418: "I'm a Teapot"}
	status.value: status.phrase
	for status in http.HTTPStatus
}

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

All_Responses = Union[
    Response, HTMLResponse, 
    ImageResponse, JsonResponse,
    SuccessJsonResponse
]