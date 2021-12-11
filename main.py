import re
import time
import packets
import asyncio
from ext import glob
from server.server import Server
from server.server import Request
from server.server import Response

import utils
import config
import pyimgur
import queries
from objects import File
from pathlib import Path
from aiohttp import ClientSession
from objects.jsonfile import JsonFile
async def on_start_up() -> None:
    glob.http = ClientSession()

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

    if config.imgur_client_id is not None:
        glob.imgur = pyimgur.Imgur(config.imgur_client_id)
    else:
        glob.imgur = None

    data_folder = Path.cwd() / '.data'
    if not data_folder.exists():
        data_folder.mkdir(exist_ok=True)
    
    glob.pfps = JsonFile(data_folder / 'pfps.json')
    glob.beatmaps = JsonFile(data_folder / 'beatmaps.json')
    glob.profiles = JsonFile(data_folder / 'profiles.json')

    if (
        not glob.pfps or
        config.player_name not in glob.pfps or
        glob.pfps[config.player_name] is None
    ):
        glob.pfps.update({config.player_name: None})

    if (
        not glob.profiles or 
        config.player_name not in glob.profiles
    ):
        glob.profiles.update(
            queries.init_profile(config.player_name)
        )
    
    utils.update_files()
    glob.current_profile = glob.profiles[config.player_name]
    
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
            if handler == path:
                st = time.time()
                resp = await glob.handlers[handler](request)
                print(f'{time.time()-st:.3f} time took to handle', path)
                return resp
            else:
                continue
        
        if (m := handler.match(path)):
            request.args |= m.groupdict()
            st = time.time()
            resp = await glob.handlers[handler](request)
            print(f'{time.time()-st:.3f} time took to handle', path)
            return resp
        
        continue
        
    print(path, 'not handled')
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

    # TODO: maybe find some hack to find a work around not having the body?
    # its a local server anyways for fun so even if i don't find it its w/e
    if glob.player.queue:
        return Response(200, glob.player.clear())
    
    return DEFAULT_RESPONSE

@server.get(
    path = re.compile(r'\/a\/(?P<userid>[0-9]*)')
)
async def avatar(request: Request) -> Response:
    image_bytes = await glob.handlers['avatar'](int(request.args['userid']))
    return Response(200, image_bytes)

from handlers import cho
from handlers import web
from handlers import ava
from handlers import submit_score

if __name__ == '__main__':
    server.run(
        bind = ('127.0.0.1', 5000),
        listening = 16,
        before_startup = on_start_up,
        background_tasks = [while_server_running]
    )
