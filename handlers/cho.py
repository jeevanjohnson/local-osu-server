import config
import packets
from ext import glob
from utils import handler
from objects import Player

@handler('login')
async def login() -> tuple[bytes, str]:
    body = bytearray()
    glob.player = p = Player()

    body += packets.userID(p.userid)
    body += packets.notification('have fun!')
    body += packets.protocolVersion()
    body += packets.banchoPrivs(p)
    body += packets.friendsList(0)

    if config.menu_icon is not None:
        body += packets.menuIcon(config.menu_icon)

    body += packets.channelInfo('#osu', 'zzz', 1)
    body += packets.channelInfoEnd()
    body += packets.channelJoin('#osu')

    await glob.player.update()
    body += packets.userPresence(p)
    body += packets.userStats(p)

    return bytes(body), 'success'