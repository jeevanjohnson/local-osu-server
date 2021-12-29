from server import Router
from server import Response

website = Router('/')

@website.get('favicon.ico')
async def favicon() -> Response:
    return Response(200, b'')