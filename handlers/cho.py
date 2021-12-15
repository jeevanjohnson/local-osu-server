import config
import packets
import asyncio
from ext import glob
from utils import handler
from objects import Player
from typing import Optional
from server.server import Request
from server.server import Response

CHANNELS: list[tuple[str, str]] = [
    # name, desc
    ('#osu', 'x'),
    ('#recent', 'shows recently submitted scores!'),
    ('#tops', 'shows top plays, as well as updates them!')
]

# Since these 2 request work together,
# even tho they are seprate like cho, web
# they should be together

profile_name: Optional[str] = None
@handler('/web/bancho_connect.php')
async def bancho_connect(request: Request) -> Response:
    global profile_name
    profile_name = request.params['u']
    return Response(200, b'')

@handler('login')
async def login() -> tuple[bytearray, str]:
    global profile_name
    body = bytearray()

    wait_loops = 0
    while (
        profile_name == None and
        wait_loops < 5
    ):
        await asyncio.sleep(0.2)
        wait_loops += 1
    
    if not profile_name:
        body += packets.userID(-5)
        body += packets.notification((
            'Seems either you are trying to login\n'
            'to a new profile or an existing one with a little conflict\n'
            'Please restart your game!'
        ))
        return body, 'fail'

    glob.player = p = Player(profile_name)

    body += packets.userID(p.userid)
    body += packets.notification((
        'Sadly, to switch profiles '
        'you will need to restart your game.\n'
        'Other then that have fun!'
    ))
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

    profile_name = None
    return body, 'success'