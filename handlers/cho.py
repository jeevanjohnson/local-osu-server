import time
import utils
import config
import packets
import asyncio
from ext import glob
from utils import log
from utils import Color
from server import Alias
from server import Query
from server import Router
from objects import Player
from typing import Optional
from server import Response
import urllib.parse as urlparse

from constants import BODY
from constants import CHANNELS
from constants import CHO_TOKEN

cho = Router((
    '/c4', '/c5', '/c6', '/ce', '/c' # type: ignore
))

profile_name: Optional[str] = None
parse_name = lambda n: urlparse.unquote(n).strip()

@cho.get('/')
async def cho_handler(
    osu_token: str = ''
) -> Response:
    if not osu_token:
        body: bytes
        token: str
        body, token = await login()
        return Response(
            code = 200, 
            body = body, 
            headers = {"cho-token": token}
        )

    if not glob.player:
        return Response(200, packets.systemRestart())

    if glob.player.queue:
        return Response(200, glob.player.clear())

    return Response(200, b'')

# should be in web, but works with cho
# to have login work "properly"
from handlers.web import web
@web.get('/bancho_connect.php')
async def bancho_connect(
    username: str = Query(parse_name, Alias('u'))
) -> Response:
    global profile_name
    profile_name = username
    log('Got a player name of', username, color = Color.LIGHTBLUE_EX)
    return Response(200, b'')

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

    await glob.player.update(glob.mode)
    body += packets.userPresence(p)
    profile_name = None

    body += utils.local_message(
        'Menus are gone! (finally lol)\n'
        'please ues the built in commands in direct from now on\n'
        'to see all the commands, type !help in the direct search bar.'
    )

    log(glob.player.name, 'successfully logged in!', color = Color.GREEN)
    return body, 'success'