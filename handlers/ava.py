import re
import utils
from ext import glob
from typing import Union
from server import Router
from server import Response
from server import ImageResponse

avatar = Router('/a')

DEFAULT_404_RESPONSE = Response(404, b'')
response = Union[Response, ImageResponse]

@avatar.get(re.compile(r'\/(?P<userid>[0-9]*)'))
async def avatar_handler(userid: int) -> response:
    if not glob.player:
        return DEFAULT_404_RESPONSE
    
    if userid != 2:
        url = f'https://a.ppy.sh/{userid}?.png'
        async with glob.http.get(url) as resp:
            if not resp or resp.status != 200:
                return ImageResponse(
                    glob.default_avatar, 'png'
                )

            return ImageResponse(
                await resp.content.read(), 'png'
            )

    if (
        glob.player.name not in glob.pfps or
        glob.pfps[glob.player.name] is None
    ):
        return ImageResponse(
            glob.default_avatar, 'png'
        )

    pfp: str = glob.pfps[glob.player.name]
    if (path := utils.is_path(pfp)):
        return ImageResponse(
            path.read_bytes(), path.suffix
        )

    async with glob.http.get(pfp) as resp:
        if not resp or resp.status != 200:
            return ImageResponse(
                glob.default_avatar, 'png'
            )
        
        return ImageResponse(
            await resp.content.read(), 'png'
        )