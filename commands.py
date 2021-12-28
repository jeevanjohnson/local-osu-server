import orjson
import config
import packets
import asyncio
from ext import glob
from objects import Mods
from typing import Union
from server import Request
from typing import Callable
from typing import Optional
from server import Response
from objects import Command
from objects import DirectResponse

def edit_func(func: Callable) -> Callable:
    
    async def edit(*args) -> Optional[bytes]:
        if not glob.player:
            resp = DirectResponse.from_str('player not online!')
            return resp.as_binary

        try:
            return await func(*args)
        except Exception as e:
            resp = DirectResponse.from_str(
                f'error: {e}'
            )
            return resp.as_binary

    return edit

def command(
    name: Union[str, list[str]], 
    docs: Optional[str] = None,
    confirm_with_user: bool = False
) -> Callable:
    def inner(func: Callable) -> Callable:
        
        if isinstance(name, list):
            for n in name:
                glob.commands[n] = Command(
                    n, edit_func(func), docs,
                    confirm_with_user, name
                )
        else:
            glob.commands[name] = Command(
                name, edit_func(func), docs,
                confirm_with_user
            )

        return func
    return inner

@command(
    name = ['help', 'h'],
    docs = 'shows all commands avaliable!'
)
async def help() -> DirectResponse:
    msg = []
    existing_docs = []
    for cmd in glob.commands.values():
        if cmd.docs in existing_docs:
            continue
        
        alias = ' / '.join([
            f"{config.command_prefix}{n}" for n in cmd.names
        ])

        if cmd.docs:
            msg.append(
                f'{alias} // {cmd.docs}'
            )
        else:
            msg.append(alias)
        
        existing_docs.append(cmd.docs)

    all_commands = DirectResponse.from_str('\n'.join(msg))
    return all_commands

@command(
    name = ['tops', 't'],
    docs = 'shows your top plays!'
)
async def tops(
    mode: Optional[Union[str, Mods]] = glob.mode, 
    limit: str = '100'
) -> DirectResponse:
    fake_req = Request()
    fake_req.params = {
        'limit': int(limit),
        'u': glob.player.name # type: ignore
    }
    if mode:
        fake_req.params['m'] = mode

    fake_response: Response = \
        await glob.handlers['/api/v1/tops'](fake_req)
    
    json = orjson.loads(fake_response.body)
    return DirectResponse.from_plays(json['plays'])

@command(
    name = ['r', 'rs', 'recent'],
    docs = 'shows your recent plays!'
)
async def recent(
    mode: Optional[Union[str, Mods]] = glob.mode, 
    limit: str = '100'
) -> DirectResponse:
    fake_req = Request()
    fake_req.params = {
        'limit': int(limit),
        'u': glob.player.name # type: ignore
    }
    if mode:
        fake_req.params['m'] = mode

    fake_response: Response = \
        await glob.handlers['/api/v1/recent'](fake_req)
    
    json = orjson.loads(fake_response.body)
    return DirectResponse.from_plays(json['plays'])

@command(
    name = ['stats', 'p', 'osu', 'profile', 's'],
    docs = 'shows your stats!'
)
async def stats(
    mode: Optional[Union[str, Mods]] = glob.mode
) -> DirectResponse:
    fake_req = Request()
    fake_req.params = {
        'u': glob.player.name # type: ignore
    }
    if mode:
        fake_req.params['m'] = mode

    fake_response: Response = \
        await glob.handlers['/api/v1/profile'](fake_req)
    
    json = orjson.loads(fake_response.body)
    msg = (
        f"name: {json['name']}\n"
        f"rank: {json['rank']}\n"
        f"playcount: {json['playcount']}\n"
        f"pp: {json['pp']}\n"
        f"mode: {json['mode']}"
    )
    return DirectResponse.from_str(msg)

@command(
    name = 'recalc',
    docs = 'recalculate all profiles that have been created!',
    confirm_with_user = True
)
async def recalc() -> None:
    fake_req = Request()
    fake_req.params = {
        'u': glob.player.name # type: ignore
    }

    await glob.handlers['/api/v1/recalc'](fake_req)
    glob.player.queue += packets.notification( # type: ignore
        "Stats will be updated once recalculation is finished!"
    )
    return

@command(
    name = 'wipe',
    docs = 'wipes all stats from your current profile!',
    confirm_with_user = True
)
async def wipe() -> None:
    fake_req = Request()
    fake_req.params = {
        'u': glob.player.name, # type: ignore
        'yes': 'yes'
    }

    await glob.handlers['/api/v1/wipe'](fake_req)
    glob.player.queue += packets.notification( # type: ignore
        "Profile was wiped!"
    )
    
    async def update_player() -> None:
        await glob.player.update(glob.mode) # type: ignore
        glob.player.queue += packets.userStats(glob.player) # type: ignore
    
    asyncio.create_task(update_player())
    return 

AVATAR_DOCS = (
    "change current profile's avatar! / "
    f"example: {config.command_prefix}avatar (path or link to image here)"
)

@command(
    name = 'avatar',
    docs = AVATAR_DOCS,
    confirm_with_user = True
)
async def avatar(img: str) -> None:
    glob.pfps[glob.player.name] = img # type: ignore
    glob.player.queue += packets.notification( # type: ignore
        f'avatar was changed to: {img}\n'
        'restart your game for image to show!'
    )
    return 