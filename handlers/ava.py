import utils
from ext import glob
from utils import handler
from server import Response
from server import ImageResponse

DEFAULT_404_RESPONSE = Response(404, b'')

@handler('avatar')
async def avatar(userid: int) -> Response:
    if not glob.player:
        return DEFAULT_404_RESPONSE

    if userid != 2:
        url = f'https://a.ppy.sh/{userid}?.png'
        async with glob.http.get(url) as resp:
            if not resp or resp.status != 200:
                return ImageResponse(
                    glob.default_avatar,
                    image_extenton = '.png'
                )

            return ImageResponse(
                await resp.content.read(),
                image_extenton = '.png'
            )

    if (
        glob.player.name not in glob.pfps or
        glob.pfps[glob.player.name] is None
    ):
        return ImageResponse(
            glob.default_avatar,
            image_extenton = '.png'
        )

    pfp: str = glob.pfps[glob.player.name]
    if (path := utils.is_path(pfp)):
        return ImageResponse(
            path.read_bytes(),
            image_extenton = path.suffix
        )

    async with glob.http.get(pfp) as resp:
        if not resp or resp.status != 200:
            return ImageResponse(
                glob.default_avatar,
                image_extenton = '.png'
            )
        
        return ImageResponse(
            await resp.content.read(),
            image_extenton = '.png'
        )
