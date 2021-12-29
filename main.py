#!/usr/bin/env python

import os
import orjson
import asyncio
from ext import glob
from server import HTTPServer
from utils import log_success

import config
import updater
import pyimgur
from pathlib import Path
from aiohttp import ClientSession
from objects.jsonfile import JsonFile

glob.http_server = http_server = HTTPServer()

@http_server.starting
async def on_start_up() -> None:
    glob.http = ClientSession(json_serialize=orjson.loads)

    if (
        config.auto_update and
        await updater.needs_updating()
    ):
        await updater.update()
        raise SystemExit

    if config.paths['osu! path']:
        osu_path = Path(config.paths['osu! path'])
        glob.songs_folder = Path(
            config.paths['songs'] or str(osu_path / 'Songs')
        )
        glob.screenshot_folder = Path(
            config.paths['screenshots'] or str(osu_path / 'Screenshots')
        )
        glob.replay_folder = Path(
            config.paths['replay'] or str(osu_path / 'Replays')
        )
        
        if not glob.replay_folder.exists():
            glob.replay_folder.mkdir(exist_ok=True)

    else:
        glob.songs_folder = (
            Path(config.paths['songs']) if 
            config.paths['songs'] else 
            None
        )

        glob.replay_folder = (
            Path(config.paths['replay']) if 
            config.paths['replay'] else 
            None
        )
    
        glob.screenshot_folder = (
            Path(config.paths['screenshots']) if 
            config.paths['screenshots'] else 
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
    
    import version as local_version
    log_success(f'running on version {local_version.version}')

@http_server.shutdown
async def shutdown_method() -> None:
    await glob.http.close()
    log_success((
        'server successfully shutdown!\n'
        'see you next time :)'
    ))

async def check_for_score_sub() -> None:
    from objects import Score
    from handlers import score_submit

    if not glob.replay_folder or not glob.replay_folder.exists():
        print(
            "replay folder doesn't exist\n"
            "please restart server to have score sub working."
        )
    
    timestamp = lambda: glob.replay_folder.stat().st_mtime # type: ignore
    last_changed = timestamp()

    while await asyncio.sleep(0.1, result=True):
        if not glob.player:
            continue
        
        if last_changed == (time_changed := timestamp()):
            continue

        last_changed = time_changed

        replay: Path = glob.replay_folder / max( # type: ignore
            glob.replay_folder.glob('*.osr'), # type: ignore
            key = os.path.getctime
        )

        if not replay.exists():
            print("replay file doesn't exist!")

        await score_submit(
            Score.from_replay(replay)
        )

def main() -> int:
    import handlers # load all handlers
    from website import website_handler

    for router in [
        handlers.api.api,
        handlers.cho.cho,
        handlers.web.web,
        handlers.ava.avatar,
        website_handler.website
    ]:
        http_server.add_router(router)
    
    # load all commands
    import commands

    try:
        import uvloop # type: ignore
        uvloop.install()
    except:
        pass

    http_server.run(
        background_tasks = [check_for_score_sub]
    )

    return 0

if __name__ == '__main__':
    SystemExit(main())