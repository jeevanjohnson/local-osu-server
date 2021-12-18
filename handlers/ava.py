import utils
from ext import glob
from utils import handler
from server import Response

@handler('avatar')
async def avatar(userid: int) -> Response:
    if not glob.player:
        return Response(404, b'')
    
    if userid != 2:
        url = f'https://a.ppy.sh/{userid}?.png'
        async with glob.http.get(url) as resp:
            if not resp or resp.status != 200:
                return Response(200, glob.default_avatar)

            return Response(200, await resp.content.read())
    
    if (
        glob.player.name not in glob.pfps or
        glob.pfps[glob.player.name] is None
    ):
        return Response(200, glob.default_avatar)
    
    pfp: str = glob.pfps[glob.player.name]
    if (path := utils.is_path(pfp)):
        return Response(200, path.read_bytes())

    async with glob.http.get(pfp) as resp:
        if not resp or resp.status != 200:
            return Response(200, glob.default_avatar)

        return Response(200, await resp.content.read())
