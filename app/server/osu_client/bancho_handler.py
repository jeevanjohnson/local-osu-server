from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse
from fastapi import Request, Response
from fastapi import Header, Depends
from uuid import uuid4

import app.server.login as login
from app.server.login import LoginData

bancho_handling_router = APIRouter(default_response_class=Response, prefix="/c")


@bancho_handling_router.post("/")
async def handle_request(request: Request):
    print(request.headers)
    if "osu_token" not in request.headers:
        response = await handle_login(request)

    print("================================")
    return response if response else False
    # else:
    #     TODO response = implement bancho request handler
    # return response


async def handle_login(request: Request):
    raw_login_data = await request.body()

    login_data: LoginData = login.parse_login(raw_login_data)


    # import hashlib
    # hashlib.md5()
    # verify login

    response = bytearray()

'''
if user not exist -> CREATE new account
'''

    # TODO: Finish Everything Related To Send Packets to the Player
