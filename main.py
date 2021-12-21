import re

import orjson
import packets
import asyncio
from ext import glob
from utils import log
from utils import Color
from server import Server
from server import Request
from server import Response

import utils
import config
import pyimgur
import colorama
from objects import File
from pathlib import Path
from aiohttp import ClientSession
from objects.jsonfile import JsonFile

# TODO: simplify path init
async def on_start_up() -> None:
    glob.http = ClientSession()
    colorama.init(autoreset=True)

    if config.paths['osu! path'] is not None:
        osu_path = Path(config.paths['osu! path'])
        glob.songs_folder = Path(
            config.paths['songs'] or str(osu_path / 'Songs')
        )
        glob.screenshot_folder = Path(
            config.paths['screenshots'] or str(osu_path / 'Screenshots')
        )
        glob.replay_folder = File(
            config.paths['replay'] or str(osu_path / 'Replays')
        )
    else:
        glob.songs_folder = (
            Path(config.paths['songs']) if 
            config.paths['songs'] is not None else 
            None
        )

        glob.replay_folder = (
            File(config.paths['replay']) if 
            config.paths['replay'] is not None else 
            None
        )
    
        glob.screenshot_folder = (
            Path(config.paths['screenshots']) if 
            config.paths['screenshots'] is not None else 
            None
        )

    if config.imgur_client_id:
        glob.imgur = pyimgur.Imgur(config.imgur_client_id)
    else:
        glob.imgur = None

    if glob.songs_folder:
        glob.modified_txt = glob.songs_folder / 'modified_mp3_list.txt'

    data_folder = Path.cwd() / '.data'
    if not data_folder.exists():
        data_folder.mkdir(exist_ok=True)
    
    glob.pfps = JsonFile(data_folder / 'pfps.json')
    glob.beatmaps = JsonFile(data_folder / 'beatmaps.json')
    glob.profiles = JsonFile(data_folder / 'profiles.json')
    glob.modified_beatmaps = JsonFile(data_folder / 'modified.json')

    async with glob.http.get('https://a.ppy.sh/') as resp:
        if not resp or resp.status != 200:
            glob.default_avatar = b''
            return
        
        glob.default_avatar = await resp.content.read()

async def while_server_running() -> None:
    if glob.replay_folder is None:
        utils.add_to_player_queue(packets.notification((
            'No scores can be submitted due\n'
            'to no replay folder provided!'
        )))
        return
    
    while await asyncio.sleep(0.5, result=True):
        if glob.replay_folder.is_changed() and glob.player:
            await glob.handlers['score_sub']() 

server = Server()
DEFAULT_RESPONSE = Response(200, b'')
@server.get(
    path = re.compile(r'\/osu\/(?P<handler>.*)')
)
async def osu(request: Request) -> Response:
    path = f"/{request.args['handler']}"

    for handler in glob.handlers:
        if isinstance(handler, str):
            if handler != path:
                continue
            
            resp = await glob.handlers[handler](request)
            return resp
        
        if (m := handler.match(path)):
            request.args |= m.groupdict()
            resp = await glob.handlers[handler](request)
            return resp
        
        continue
        
    log(path, "isn't handled", color = Color.RED)
    return DEFAULT_RESPONSE

@server.get(
    path = re.compile(r'\/((c[4-6e])|(c))\/(?P<handler>.*)'),
)
async def bancho(request: Request) -> Response:
    if 'osu_token' not in request:
        body: bytes
        token: str
        body, token = await glob.handlers['login']()
        return Response(
            code = 200, 
            body = body, 
            headers = {"cho-token": token}
        )

    if not glob.player:
        return Response(200, packets.systemRestart())

    if glob.player.queue:
        return Response(200, glob.player.clear())
    
    return DEFAULT_RESPONSE

@server.get(
    path = re.compile(r'\/a\/(?P<userid>[0-9]*)')
)
async def avatar(request: Request) -> Response:
    return await glob.handlers['avatar'](
        int(request.args['userid'])
    )

DEFAULT_API_RESPONSE = Response(
    code = 200,
    body = orjson.dumps({
        'status': 'failed',
        'message': "unknown api path!"
    }),
    headers = {'Content-type': 'application/json charset=utf-8'}
)
@server.get(
    path = re.compile(r'\/api\/v1\/(?P<path>.*)')
)
async def apiv1(request: Request) -> Response:
    api_path = f"/api/v1/{request.args['path']}"
    if api_path not in glob.handlers:
        return DEFAULT_API_RESPONSE
    else:
        return await glob.handlers[api_path](request)

@server.get(
    path = re.compile(r'\/(?P<path>.*)')
)
async def website(request: Request) -> Response:
    return await glob.handlers[
        f"/{request.args['path']}"
    ](request)

import handlers # load all handlers

if __name__ == '__main__':
    try:
        import uvloop # type: ignore
        uvloop.install()
    except:
        pass

    server.run(
        bind = ('127.0.0.1', 5000),
        listening = 16,
        before_startup = on_start_up,
        background_tasks = [while_server_running]
    )
