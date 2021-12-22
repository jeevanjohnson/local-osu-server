import config
import packets
import asyncio
from ext import glob
from utils import log
from utils import Color
from utils import handler
from server import Request
from objects import Player
from typing import Optional
from server import Response
import urllib.parse as urlparse

WELCOME_MSG = '\n'.join([
    'Welcome {name}!',
    '',
    'Below you can find some useful buttons to enhance your gaming experience B)'
])

CHANNEL = tuple[str, str]
CHANNELS: list[CHANNEL] = [
    # name, desc
    ('#osu', 'x'),
    ('#recent', 'shows recently submitted scores!'),
    ('#tops', 'shows top plays, as well as updates them!')
]

BUTTON = tuple[str, str]
BUTTONS: list[BUTTON] = [
    # url, name
    ('http://127.0.0.1:5000/api/v1/client/tops?limit=100', 'view tops'),
    ('http://127.0.0.1:5000/api/v1/client/recent?limit=10', 'view recent'),
    ('http://127.0.0.1:5000/api/v1/client/recalc', 'recalc plays'),
    ('http://127.0.0.1:5000/api/v1/client/profile', 'view profile'),
    ('http://127.0.0.1:5000/api/v1/client/change_avatar', 'change avatar'),
    ('http://127.0.0.1:5000/api/v1/client/wipe', 'wipe profile')
]

CHO_TOKEN = str
BODY = bytearray

profile_name: Optional[str] = None

# should be in web, but works with cho
# to have login work "properly"
@handler('/web/bancho_connect.php')
async def bancho_connect(request: Request) -> Response:
    global profile_name
    profile_name = urlparse.unquote(request.params['u']).strip()
    log('Got a player name of', profile_name, color = Color.LIGHTBLUE_EX)
    return Response(200, b'')

@handler('login')
async def login() -> tuple[BODY, CHO_TOKEN]:
    global profile_name
    body = bytearray()

    wait_loops = 0

    while (
        profile_name is None and
        wait_loops < 5
    ):
        await asyncio.sleep(0.2)
        wait_loops += 1

    if profile_name is None:
        body += packets.userID(-5)
        body += packets.notification(
            'Please restart your game to login!'
        )
        log('Player needs to restart game!', color = Color.YELLOW)
        return body, 'fail'

    glob.player = p = Player(profile_name, from_login=True)
    glob.current_profile = glob.profiles[p.name]

    body += packets.userID(p.userid)
    body += packets.notification((
        'When it comes to funorange speed up maps, '
        'you might have to recreate a map in order for it to '
        'show proper rankings, other then that have fun!'
    ))
    body += packets.protocolVersion()
    body += packets.banchoPrivs(p)
    body += packets.friendsList(0)

    if (
        config.menu_icon and
        config.menu_icon['image_link'] and
        config.menu_icon['click_link']
    ):
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
    profile_name = None

    glob.player.queue += packets.sendMsg(
        client = 'local',
        msg = WELCOME_MSG.format(name=glob.player.name),
        target = '#osu',
        userid = -1,
    )

    for url, name in BUTTONS:
        glob.player.queue += packets.sendMsg(
            client = 'local',
            msg = f'[{url} {name}]',
            target = '#osu',
            userid = -1,
        )

    log(glob.player.name, 'successfully logged in!', color = Color.GREEN)
    return body, 'success'