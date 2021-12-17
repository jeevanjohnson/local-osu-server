import config
import packets
import asyncio
from ext import glob
from utils import handler
from objects import Player

CHANNELS: list[tuple[str, str]] = [
    # name, desc
    ('#osu', 'x'),
    ('#recent', 'shows recently submitted scores!'),
    ('#tops', 'shows top plays, as well as updates them!')
]

CHO_TOKEN = str
BODY = bytearray
@handler('login')
async def login() -> tuple[BODY, CHO_TOKEN]:
    body = bytearray()

    wait_loops = 0

    if not glob.player:
        while (
            glob.profile_name == None and
            wait_loops < 5
        ):
            await asyncio.sleep(0.2)
            wait_loops += 1
    else:
        while (
            glob.player.name in (glob.profile_name, None) and
            wait_loops < 5
        ):
            await asyncio.sleep(0.2)
            wait_loops += 1

    if (
        not glob.profile_name or
        (glob.player and glob.player.name == glob.profile_name)
    ):
        body += packets.userID(-5)
        body += packets.notification(
            'Please restart your game to login!'
        )

        return body, 'fail'

    glob.player = p = Player(glob.profile_name)

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
    glob.profile_name = None

    return body, 'success'