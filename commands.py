import orjson
import config
import packets
from ext import glob
from objects import Mods
from typing import Union
from typing import Callable
from typing import Optional
from objects import Command
from server import All_Responses
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

def get_func(type: str) -> Optional[Callable]:
    for router in glob.http_server.routers:
        if router.match(f'/api/v1/{type}'):
            for route in router.routes:
                if route.match(f'/{type}'):
                    return route.handler
    return

get_tops = get_func('tops')
get_recent = get_func('recent')
get_stats = get_func('profile')
run_recalc = get_func('recalc')
run_wipe = get_func('wipe')

if (
    not get_tops or
    not get_recent or
    not get_stats or
    not run_recalc or
    not run_wipe
):
    raise Exception('HOW')

@command(
    name = ['tops', 't'],
    docs = 'shows your top plays!'
)
async def tops(
    mode: Optional[Union[str, Mods]] = None, 
    limit: str = '100'
) -> DirectResponse:

    params = {
        'limit': int(limit),
        'u': glob.player.name # type: ignore
    }
    if mode:
        params['m'] = mode

    if not mode and glob.mode:
        mode = repr(glob.mode).lower()

    resp: All_Responses = await get_tops(
        name = glob.player.name, # type: ignore
        limit = int(limit),
        mode = mode or 'vn'
    )

    json = orjson.loads(resp.body)
    
    return DirectResponse.from_plays(json['plays'])

@command(
    name = ['r', 'rs', 'recent'],
    docs = 'shows your recent plays!'
)
async def recent(
    mode: Optional[Union[str, Mods]] = None, 
    limit: str = '100'
) -> DirectResponse:
    
    params = {
        'limit': int(limit),
        'u': glob.player.name # type: ignore
    }
    if mode:
        params['m'] = mode

    if not mode and glob.mode:
        mode = repr(glob.mode).lower()
    
    resp: All_Responses = await get_recent(
        name = glob.player.name, # type: ignore
        limit = int(limit),
        mode = mode or 'vn'
    )
    json = orjson.loads(resp.body)
    
    return DirectResponse.from_plays(json['plays'])

@command(
    name = ['stats', 'p', 'osu', 'profile', 's'],
    docs = 'shows your stats!'
)
async def stats(
    mode: Optional[Union[str, Mods]] = None
) -> DirectResponse:
    params: dict[str, Union[str, int]] = {
        'u': glob.player.name # type: ignore
    }
    if mode:
        params['m'] = mode

    if not mode and glob.mode:
        mode = repr(glob.mode).lower()
    
    resp: All_Responses = await get_stats(
        name = glob.player.name, # type: ignore
        mode = mode or 'vn'
    )
    
    json = orjson.loads(resp.body)
    
    msg = (
        f"name: {json['name']}\n"
        f"rank: {json['rank']}\n"
        f"playcount: {json['playcount']}\n"
        f"pp: {json['pp']}\n"
        f"acc: {json['acc']:.2f}\n"
        f"mode: {json['mode']}"
    )
    return DirectResponse.from_str(msg)

@command(
    name = 'recalc',
    docs = 'recalculate all profiles that have been created!',
    confirm_with_user = True
)
async def recalc() -> None:

    await run_recalc()
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
    await run_wipe(
        name = glob.player.name, # type: ignore
        yes = 'yes'
    )

    glob.player.queue += packets.notification( # type: ignore
        "Profile was wiped!"
    )
    
    glob.current_profile = glob.profiles[glob.player.name] # type: ignore
    await glob.player.update(glob.mode) # type: ignore
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