import config
import packets
from ext import glob
from utils import handler
from objects import Player

CHANNELS: list[tuple[str, str]] = [
    # name, desc
    ('#osu', 'x'),
    ('#recent', 'shows recently submitted scores!'),
    ('#tops', 'shows top plays, as well as updates them!')
]

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
        body += packets.menuIcon(
            tuple(config.menu_icon.values())
        )

    for channel in CHANNELS:
        cname, cdesc = channel
        body += packets.channelInfo(cname, cdesc, 1)
    
    body += packets.channelInfoEnd()
    
    for channel in CHANNELS:
        body += packets.channelJoin(channel[0])

    await glob.player.update()
    body += packets.userPresence(p)
    body += packets.userStats(p)

    return bytes(body), 'success'