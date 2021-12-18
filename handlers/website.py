import utils
import tkinter
from ext import glob
from utils import handler
from server import Request
from server import Response
from tkinter import filedialog

root = tkinter.Tk()
root.withdraw()

@handler('/favicon.ico')
async def favicon(request: Request) -> Response:
    return Response(200, b'')

CHANGE_AVATAR_HTML = (
    '<a href="http://127.0.0.1:5000/change_avatar/from_path?u={name}">'
    '<button>from path</button>'
    '</a>'
    '<br>'
    'TODO: from link lol'
)

@handler('/change_avatar')
async def change_avatar(request: Request) -> Response:
    if not glob.player:
        return Response(200, b'plaese login to your client to continue')
    
    return Response(
        200, CHANGE_AVATAR_HTML.format(
            name = glob.player.name
        ).encode()
    )

@handler('/change_avatar/from_path')
async def from_path(request: Request) -> Response:
    if 'u' not in request.params:
        return Response(200, b'please provide profile name')
    
    img_path = filedialog.askopenfilename(
        initialdir = '/', 
        title = 'Select An Image',
        filetypes = (
            ("Image", "*.*"), 
            ("All Files", "*")
        )
    )

    if not img_path:
        return Response(200, b'please provide an image')
    
    name: str = request.params['u']

    if name not in glob.pfps:
        return Response(
            200, f'no profile named `{name}` exist in db'.encode()
        )
    
    glob.pfps[name] = img_path
    utils.update_files()

    return Response(200, b'pfp was updated, restart your game to see changes!')