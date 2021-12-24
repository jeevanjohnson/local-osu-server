from utils import handler
from server import Request
from server import Response

@handler('/favicon.ico')
async def favicon(request: Request) -> Response:
    return Response(200, b'')