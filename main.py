#!/usr/bin/env python

# since aiming user friendly, 
# install all packages needed for them
# before running anything

import sys
import subprocess

print('ensuring all needed packages are installed!')
subprocess.run(
    f'{sys.executable} -m pip install -r requirements.txt',
    stdin = subprocess.DEVNULL,
    stderr = subprocess.DEVNULL,
    stdout = subprocess.DEVNULL
)

import os
import orjson
import updater
import pyimgur
import asyncio
from ext import glob
from pathlib import Path
from objects import Config
from utils import NONE_FILE
from objects import JsonFile
from server import HTTPServer
from utils import log_success
from utils import setup_config
from aiohttp import ClientSession

glob.http_server = http_server = HTTPServer()

@http_server.starting
async def on_start_up() -> None:
    glob.http = ClientSession()

    data_folder = Path.cwd() / '.data'
    if not data_folder.exists():
        data_folder.mkdir(exist_ok=True)

    config_path = data_folder / 'config.json'
    if config_path.exists():
        print('config found!')
        glob.config = Config.from_path(config_path)
        if glob.config.__dict__.keys() != Config().__dict__.keys():
            print('config was updated! please redo config')
            glob.config = setup_config()
    else:
        glob.config = setup_config()
        config_path.write_bytes(
            orjson.dumps(glob.config.__dict__)
        )

    glob.json_config = JsonFile(config_path)

    if (
        glob.config.auto_update and
        await updater.needs_updating()
    ):
        await updater.update()
        raise SystemExit

    if glob.config.paths['osu_path']:
        osu_path = Path(glob.config.paths['osu_path'])
        glob.songs_folder = Path(
            glob.config.paths['songs'] or str(osu_path / 'Songs')
        )
        glob.screenshot_folder = Path(
            glob.config.paths['screenshots'] or str(osu_path / 'Screenshots')
        )
        glob.replay_folder = Path(
            glob.config.paths['replay'] or str(osu_path / 'Replays')
        )
        
        if not glob.replay_folder.exists():
            glob.replay_folder.mkdir(exist_ok=True)

    else:
        glob.songs_folder = (
            Path(glob.config.paths['songs']) if 
            glob.config.paths['songs'] else 
            NONE_FILE
        )

        glob.replay_folder = (
            Path(glob.config.paths['replay']) if 
            glob.config.paths['replay'] else 
            NONE_FILE
        )
    
        glob.screenshot_folder = (
            Path(glob.config.paths['screenshots']) if 
            glob.config.paths['screenshots'] else 
            NONE_FILE
        )

    if glob.config.imgur_client_id:
        glob.imgur = pyimgur.Imgur(glob.config.imgur_client_id)
    else:
        glob.imgur = None

    if glob.songs_folder:
        glob.modified_txt = glob.songs_folder / 'modified_mp3_list.txt'
    
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

    if glob.replay_folder.exists():
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
