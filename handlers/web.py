import os
import utils
import regex
import orjson
import config
import aiohttp
import packets
import asyncio
import pyperclip
from ext import glob
from utils import log
from utils import Color
from objects import Mods
from utils import handler
from server import Request
from server import Response
from utils import log_error
from utils import log_success
import urllib.parse as urlparse
from objects import Leaderboard
from objects import NotSupported
from constants import ParsedParams
from objects import DirectResponse
from objects import ModifiedLeaderboard

async def DEFAULT_RESPONSE_FUNC(request: Request) -> Response:
    return Response(200, b'')

# unusable or unused handlers
for hand in [
    '/web/lastfm.php',
    '/web/osu-rate.php',
    '/web/osu-error.php',
    '/difficulty-rating',
    '/web/osu-session.php',
    '/web/osu-markasread.php',
    '/web/osu-getfriends.php',
    '/web/osu-getbeatmapinfo.php'
]:
    handler(hand)(DEFAULT_RESPONSE_FUNC)

OSU_API_BASE = 'https://osu.ppy.sh/api'

@handler(regex.screenshot_web_path)
async def web_screenshot(request: Request) -> Response:
    return Response(
        code = 301,
        body = b'',
        headers = {'Location': request.args['link']}
    )

@handler('/web/osu-screenshot.php')
async def osu_screenshots(request: Request) -> Response:
    if not glob.screenshot_folder:
        return Response(200, b'error: no')

    screenshots = glob.screenshot_folder.glob('*')
    latest_screenshot = glob.screenshot_folder / max(screenshots, key=os.path.getctime)

    if not glob.imgur:
        return Response(200, str(latest_screenshot))

    uploaded_image = glob.imgur.upload_image(
        path = str(latest_screenshot),
        title = 'from local server'
    )

    pyperclip.copy(uploaded_image.link)
    return Response(200, uploaded_image.link.encode())

@handler(regex.bmap_web_path)
async def bmap_web(request: Request) -> Response:
    return Response(
        code = 301,
        body = b'',
        headers = {'Location': f'https://osu.ppy.sh/{request.path[5:]}'}
    )

REMINDER = None
DEFAULT_CHARTS = '\n'.join([
    "beatmapId:0|beatmapSetId:0|beatmapPlaycount:0|beatmapPasscount:0|approvedDate:0",
    "chartId:beatmap|chartUrl:https://osu.ppy.sh/b/0|chartName:Beatmap Ranking|rankBefore:|rankAfter:0|maxComboBefore:|maxComboAfter:0|accuracyBefore:|accuracyAfter:0|rankedScoreBefore:|rankedScoreAfter:0|ppBefore:|ppAfter:0|onlineScoreId:0",
    "chartId:overall|chartUrl:https://osu.ppy.sh/u/2|chartName:Overall Ranking|rankBefore:0|rankAfter:0|rankedScoreBefore:0|rankedScoreAfter:0|totalScoreBefore:0|totalScoreAfter:0|maxComboBefore:0|maxComboAfter:0|accuracyBefore:0|accuracyAfter:0|ppBefore:0|ppAfter:0|achievements-new:|onlineScoreId:0"
]).encode()
@handler('/web/osu-submit-modular-selector.php')
async def score_sub(request: Request) -> Response:
    global REMINDER
    if (
        not glob.player or
        not glob.current_profile
    ):
        return Response(200, b"error: no")

    if REMINDER is None:
        glob.player.queue += packets.notification((
            'To submit a play be sure to save the replay of the play!'
        ))
        REMINDER = 0
    elif REMINDER == 50:
        glob.player.queue += packets.notification((
            'Just a reminder\n'
            'To submit a play be sure to save the replay of the play!'
        ))
        REMINDER = 0

    REMINDER += 1

    if 'playcount' in glob.current_profile:
        glob.current_profile['playcount'] += 1
    else:
        glob.current_profile['playcount'] = 1

    utils.update_files()

    glob.player.queue += packets.userStats(glob.player)

    log_success(f"{glob.player.name}'s playcount increased!")
    return Response(200, DEFAULT_CHARTS)

@handler('/web/osu-getseasonal.php')
async def get_bgs(request: Request) -> Response:
    if config.seasonal_bgs is None:
        bgs = b'[""]'
    else:
        bgs = orjson.dumps(config.seasonal_bgs)

    return Response(200, bgs)

@handler('/web/osu-getreplay.php')
async def get_replay(request: Request) -> Response:
    scoreid = request.params['c']

    if scoreid > 0:
        params = {
            'k': config.osu_api_key,
            's': request.params['c'],
            'm': request.params['m']
        }
        async with glob.http.get(
            url = f'{OSU_API_BASE}/get_replay',
            params = params
        ) as resp:
            if not resp or resp.status != 200:
                return Response(200, b'error: no')

            json = await resp.json()

        replay_frames = utils.string_to_bytes(json["content"])
        log('bancho replay handled', color = Color.LIGHTGREEN_EX)
        return Response(200, replay_frames)

    elif (glob.player and glob.current_profile):
        real_id = abs(scoreid) - 1
        play = glob.current_profile['plays']['all_plays'][real_id].copy()

        if (
            'replay_frames' not in play or
            play['replay_frames'] is None
        ):
            log_error(f'no replay frames were found for scoreid: {real_id}')
            return Response(200, b'error: no')
        else:
            log(
                f"{glob.player.name}'s replay was handled",
                color = Color.LIGHTGREEN_EX
            )

            if "b\'" == play['replay_frames'][:2]:
                replay: bytes = eval(play["replay_frames"])
            else:
                replay = utils.string_to_bytes(play['replay_frames'])

            return Response(
                code = 200,
                body = replay
            )
    else:
        log_error('error handling replay')
        return Response(200, b'error: no')

NOT_SUPPORTED = NotSupported().as_binary

@handler('/web/osu-osz2-getscores.php')
async def leaderboard(request: Request) -> Response:
    if not glob.player:
        return Response(404, b'')

    mode = request.params['m']
    rank_type = request.params['v']

    supported = (
        mode == 0 and
        rank_type in (0, 1, 2)
    )

    if not supported:
        return Response(200, NOT_SUPPORTED)

    parsed_params = ParsedParams(
        filename = urlparse.unquote_plus(request.params['f']),
        mods = request.params['mods'],
        mode = request.params['m'],
        rank_type = request.params['v'],
        set_id = request.params['i'],
        md5 = request.params['c'],
        name_data =  None
    )

    filename = parsed_params['filename']
    mods = request.params['mods']

    if mods & Mods.RELAX:
        if (
            not glob.mode or
            not glob.mode & Mods.RELAX
        ):
            glob.mode = Mods.RELAX
            glob.invalid_mods = (
                Mods.AUTOPILOT | Mods.AUTOPLAY |
                Mods.CINEMA | Mods.TARGET
            )._value_
            glob.player.queue += packets.notification(
                'Mode was switched to rx!'
            )
            asyncio.create_task(glob.player.update(glob.mode))
    elif mods & Mods.AUTOPILOT:
        if (
            not glob.mode or
            not glob.mode & Mods.AUTOPILOT
        ):
            glob.mode = Mods.AUTOPILOT
            glob.invalid_mods = (
                Mods.RELAX | Mods.AUTOPLAY |
                Mods.CINEMA | Mods.TARGET
            )._value_
            glob.player.queue += packets.notification(
                'Mode was switched to ap!'
            )
            asyncio.create_task(glob.player.update(glob.mode))
    elif not mods & (Mods.RELAX | Mods.AUTOPILOT):
        if glob.mode:
            glob.mode = None
            glob.invalid_mods = (
                Mods.AUTOPILOT | Mods.RELAX |
                Mods.AUTOPLAY | Mods.CINEMA |
                Mods.TARGET
            )._value_
            glob.player.queue += packets.notification(
                'Mode was switched to vanilla!'
            )
            asyncio.create_task(glob.player.update(glob.mode))

    if config.osu_api_key:
        lb = await Leaderboard.from_bancho(parsed_params)
    else:
        lb = await Leaderboard.from_offline(parsed_params)

    valid_bmap = lb.bmap and lb.bmap.approved in (1, 2, 3, 4)
    if not valid_bmap and not config.disable_funorange_maps:
        regex_results = [
            r.search(filename)
            for r in regex.modified_regexes
        ]

        name_data = regex.filename_parser.search(filename)
        if name_data and (diff_name := name_data['diff_name']):
            regex_results.extend([
                r.search(diff_name)
                for r in regex.attribute_edits
            ])

            parsed_params['name_data'] = name_data

        if any(regex_results):
            lb = await ModifiedLeaderboard.from_client(parsed_params) # type: ignore
            log_success(f'handled funorange map of {parsed_params["filename"]}')
        else:
            log_success(f'handled bancho(?) map of {parsed_params["filename"]}')
    else:
        log_success(f'handled map of setid: {parsed_params["set_id"]}')

    return Response(200, lb.as_binary)

BASE_URL = 'https://beatconnect.io'
@handler(regex.download_web_path)
async def download(request: Request) -> Response:
    setid = request.args['setid']
    
    if setid == '-1' and glob.current_cmd:
        cmd = glob.current_cmd
        await cmd.func(*cmd.args)
        cmd.args = []
        glob.current_cmd = None
        return Response(200, b'')
    
    if setid == '-1':
        return Response(200, b'')

    url = f'{BASE_URL}/b/{setid}'
    async with glob.http.get(url) as resp:
        if (
            not resp or
            resp.status != 200 or
            not (osz_binary := await resp.content.read())
        ):
            log_success(f"can't downloaded map set, id: {setid}")
            return Response(200, b'')

    log_success(f'succesfully downloaded map set, id: {setid}')
    return Response(
        code = 200,
        body = osz_binary,
    )

DIRECT_TO_API_STATUS = {
    0: 'ranked',
    2: 'unranked',
    3: 'qualified',
    4: 'all',
    5: 'unranked',
    7: 'ranked',
    8: 'loved',
}

DIRECT_TO_MIRROR_MODE = {
    0: 'std',
    1: 'taiko',
    2: 'ctb',
    3: 'mania'
}

DIRECT_BASE_API = 'https://beatconnect.io/api'

COMMAND_NOT_FOUND = DirectResponse.from_str(
    'command not found!'
).as_binary

@handler('/web/osu-search.php')
async def direct(request: Request) -> Response:
    query = urlparse.unquote_plus(request.params['q'])
    if query.startswith(config.command_prefix):
        cmd, *args = query.split()
        cmd = cmd.removeprefix(config.command_prefix)
        
        if cmd not in glob.commands:
            return Response(200, COMMAND_NOT_FOUND)
        
        command = glob.commands[cmd]
        
        if command.confirm_with_user:
            command.args = args
            glob.current_cmd = command

            msg = (
                'click me to execute!\n'
                f'loaded command: {command.name}\n'
                f'following args: {args}'
            )

            execute_button = DirectResponse.from_str(
                msg, start_id = -1
            ).as_binary

            return Response(200, execute_button)
        else:
            resp = await command.func(*args)

            if resp:
                return Response(200, bytes(resp))
            else:
                return Response(200, b'0')

    if not config.beatconnect_api_key:
        utils.add_to_player_queue(
            packets.notification("No api key given for direct!")
        )
        return Response(200, b'0')

    beatconnect_params = {
        'token': config.beatconnect_api_key,
    }
    client_params = request.params

    if query not in ("Newest", "Top Rated", "Most Played"):
        beatconnect_params['q'] = query

    if client_params['m'] != -1:
        beatconnect_params['m'] = DIRECT_TO_MIRROR_MODE[client_params['m']]

    beatconnect_params['s'] = DIRECT_TO_API_STATUS[client_params['r']]

    try:
        async with glob.http.get(
            url = f'{DIRECT_BASE_API}/search',
            params = beatconnect_params
        ) as resp:
        
            if (
                not resp or
                resp.status != 200 or
                not (resp_dict := await resp.json())
            ):
                log_error('no maps found')
                return Response(200, b'0')
        
    except aiohttp.ClientConnectorError:
        log_error('mirror currently down')
        return Response(200, b'0')
    
    log_success(f'maps loaded for query: `{query}` !')
    return Response(
        code = 200, 
        body = DirectResponse(
            bmaps = resp_dict['beatmaps']
        ).as_binary
    )