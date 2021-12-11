import utils
import config
from ext import glob
from utils import handler

@handler('avatar')
async def avatar(userid: int) -> bytes:
    if userid != 2:
        url = f'https://a.ppy.sh/{userid}?.png'
        async with glob.http.get(url) as resp:
            if not resp or resp.status != 200:
                return glob.default_avatar

            return await resp.content.read()
    
    if (
        config.player_name not in glob.pfps or
        glob.pfps[config.player_name] is None
    ):
        return glob.default_avatar
    
    pfp: str = glob.pfps[config.player_name]
    if (path := utils.is_path(pfp)):
        return path.read_bytes()

    async with glob.http.get(pfp) as resp:
        if not resp or resp.status != 200:
            return glob.default_avatar

        return await resp.content.read()
