from typing import Union
from objects import Menu
from objects import Button
from typing import Callable
from typing import Optional

main_menu = Menu('Main Menu')

def button(
    menu: Menu,
    category: str,
    name: str,
    docs: Optional[str] = None
) -> Callable:
    def inner(func: Callable) -> Callable:
        menu.add_button(
            category = category,
            button = Button(name, func, docs)
        )
        return func
    return inner

def main_menu_button(
    category: str,
    name: str,
    docs: Optional[str] = None
) -> Callable:
    def inner(func: Callable) -> Callable:
        button(main_menu, category, name, docs)(func)
        return func
    return inner

from ext import glob
from server import Request
from server import JsonResponse
from server import SuccessJsonResponse

RESPONSE = Union[JsonResponse, SuccessJsonResponse, str]

@main_menu_button(
    category = 'View Profile',
    name = 'Tops',
    docs = 'tops plays in a json response!'
)
async def tops() -> RESPONSE:
    if not glob.player:
        return JsonResponse(404, {'error': 'player is not online'})

    fake_req = Request()
    fake_req.params = {
        'limit': 100,
        'u': glob.player.name
    }
    if glob.mode:
        fake_req.params['m'] = int(glob.mode)

    return await glob.handlers['/api/v1/tops'](fake_req)

@main_menu_button(
    category = 'View Profile',
    name = 'Recent',
    docs = 'recent plays in a json response!'
)
async def recent() -> RESPONSE:
    if not glob.player:
        return JsonResponse(404, {'error': 'player is not online'})

    fake_req = Request()
    fake_req.params = {
        'limit': 10,
        'u': glob.player.name
    }
    if glob.mode:
        fake_req.params['m'] = int(glob.mode)

    return await glob.handlers['/api/v1/recent'](fake_req)

@main_menu_button(
    category = 'View Profile',
    name = 'Stats',
    docs = 'Stats in a json response!'
)
async def stats() -> RESPONSE:
    if not glob.player:
        return JsonResponse(404, {'error': 'player is not online'})

    fake_req = Request()
    fake_req.params = {
        'u': glob.player.name
    }
    if glob.mode:
        fake_req.params['m'] = int(glob.mode)
    return await glob.handlers['/api/v1/profile'](fake_req)

@main_menu_button(
    category = 'Edit Profile',
    name = 'Recalc',
    docs = 'Recalculates all scores submitted!'
)
async def recalc() -> RESPONSE:
    if not glob.player:
        return JsonResponse(404, {'error': 'player is not online'})

    fake_req = Request()
    fake_req.params = {
        'u': glob.player.name
    }
    if glob.mode:
        fake_req.params['m'] = int(glob.mode)
    return await glob.handlers['/api/v1/recalc'](fake_req)

@main_menu_button(
    category = 'Edit Profile',
    name = 'Wipe',
    docs = 'Wipes scores from profile!'
)
async def wipe() -> RESPONSE:
    if not glob.player:
        return JsonResponse(404, {'error': 'player is not online'})

    fake_req = Request()
    fake_req.params = {
        'u': glob.player.name
    }
    if glob.mode:
        fake_req.params['m'] = int(glob.mode)
    return await glob.handlers['/api/v1/wipe'](fake_req)

@main_menu_button(
    category = 'Avatar',
    name = 'Change Avatar From Path',
    docs = "change current profile's avatar from a path"
)
async def avatar_from_path() -> RESPONSE:
    return 'TODO: support at some point....'

@main_menu_button(
    category = 'Avatar',
    name = 'Change Avatar From Url',
    docs = "change current profile's avatar from a url"
)
async def avatar_from_url() -> RESPONSE:
    return 'TODO: support at some point....'