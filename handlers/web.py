import os
import re
import utils
import regex
import orjson
import aiohttp
import packets
import asyncio
import pyperclip
from ext import glob
from utils import log
from utils import Color
from objects import Mods
from server import Query
from server import Alias
from typing import Union
from server import Router
from utils import log_error
from server import Response
from utils import log_success
import urllib.parse as urlparse
from objects import Leaderboard
from objects import NotSupported
from constants import ParsedParams
from objects import DirectResponse
from objects import LeaderboardTypes
from objects import ModifiedLeaderboard

web = Router((
    '/osu/web', '/osu' # type: ignore
))

async def DEFAULT_RESPONSE_FUNC() -> Response:
    return Response(200, b'')

# unusable or unused handlers
for hand in [
    '/lastfm.php',
    '/osu-rate.php',
    '/osu-error.php',
    '/osu-session.php',
    '/difficulty-rating',
    '/osu-markasread.php',
    '/osu-getfriends.php',
    '/osu-getbeatmapinfo.php'
]:
    web.get(hand)(DEFAULT_RESPONSE_FUNC)

OSU_API_BASE = 'https://osu.ppy.sh/api'

@web.get(re.compile(r'\/ss\/(?P<link>.*)'))
async def get_ss(link: str) -> Response:
    return Response(
        code = 301,
        body = b'',
        headers = {'Location': link}
    )

@web.get(re.compile(r'(?P<full_path>\/(beatmaps|beatmapsets)\/.*)'))
async def bmap_web(full_path: str) -> Response:
    return Response(
        code = 301,
        body = b'',
        headers = {'Location': f'https://osu.ppy.sh/{full_path}'}
    )

@web.get(re.compile(r'/d/(?P<setid>[-0-9]*)'))
async def get_osz(setid: int) -> Response:
    if setid == -1 and glob.current_cmd:
        cmd = glob.current_cmd
        await cmd.func(*cmd.args)
        cmd.args = []
        glob.current_cmd = None
        return Response(200, b'')
    
    if setid == -1:
        return Response(200, b'')

    return Response(
        code = 301,
        body = b'',
        headers = {
            'Location': f'https://osu.gatari.pw/d/{setid}'
    })

@web.get('/osu-screenshot.php')
async def osu_screenshots() -> Response:
    if not glob.screenshot_folder:
        return Response(200, b'error: no')

    latest_screenshot = glob.screenshot_folder / max(
        glob.screenshot_folder.glob('*'), 
        key = os.path.getctime
    )

    if not glob.imgur:
        return Response(200, str(latest_screenshot))

    uploaded_image = glob.imgur.upload_image(
        path = str(latest_screenshot),
        title = 'from local server'
    )

    pyperclip.copy(uploaded_image.link)
    return Response(200, uploaded_image.link.encode())

REMINDER = None
DEFAULT_CHARTS = '\n'.join([
    "beatmapId:0|beatmapSetId:0|beatmapPlaycount:0|beatmapPasscount:0|approvedDate:0",
    "chartId:beatmap|chartUrl:https://osu.ppy.sh/b/0|chartName:Beatmap Ranking|rankBefore:|rankAfter:0|maxComboBefore:|maxComboAfter:0|accuracyBefore:|accuracyAfter:0|rankedScoreBefore:|rankedScoreAfter:0|ppBefore:|ppAfter:0|onlineScoreId:0",
    "chartId:overall|chartUrl:https://osu.ppy.sh/u/2|chartName:Overall Ranking|rankBefore:0|rankAfter:0|rankedScoreBefore:0|rankedScoreAfter:0|totalScoreBefore:0|totalScoreAfter:0|maxComboBefore:0|maxComboAfter:0|accuracyBefore:0|accuracyAfter:0|ppBefore:0|ppAfter:0|achievements-new:|onlineScoreId:0"
]).encode()

@web.get('/osu-submit-modular-selector.php')
async def score_sub() -> Response:
    global REMINDER
    if not glob.player:
        return Response(404, b'')

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

@web.get('/osu-getseasonal.php')
async def get_bgs() -> Response:
    if not glob.config.seasonal_bgs:
        bgs = b'[""]'
    else:
        bgs = orjson.dumps(glob.config.seasonal_bgs)

    return Response(200, bgs)

@web.get('/osu-getreplay.php')
async def get_replay(
    scoreid: int = Alias('c'),
    mode: int = Alias('m')
) -> Response:
    if scoreid > 0:
        params = {
            'k': glob.config.osu_api_key,
            's': scoreid,
            'm': mode
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

NOT_SUPPORTED = bytes(NotSupported())

@web.get('/osu-osz2-getscores.php')
async def leaderboard(
    mods: Mods,
    mode: int = Alias('m'),
    rank_type: LeaderboardTypes = Alias('v'),
    filename: str = Query(urlparse.unquote_plus, Alias('f')),
    setid: int = Alias('i'),
    md5: str = Alias('c')
) -> Response:
    if not glob.player:
        return Response(404, b'')

    valid_rank_types = (
        LeaderboardTypes.LOCAL, 
        LeaderboardTypes.TOP, 
        LeaderboardTypes.MODS
    )

    supported = (
        mode == 0 and
        rank_type in valid_rank_types
    )

    if not supported:
        return Response(200, NOT_SUPPORTED)

    parsed_params = ParsedParams(
        filename = filename,
        mods = mods,
        mode = mode,
        rank_type = rank_type,
        set_id = setid,
        md5 = md5,
        name_data =  None
    )

    if mods & Mods.RELAX:
        if (
            not glob.mode or
            not glob.mode & Mods.RELAX
        ):
            glob.mode = Mods.RELAX
            glob.invalid_mods = (
                Mods.AUTOPILOT | Mods.AUTOPLAY |
                Mods.CINEMA | Mods.TARGET
            )
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
            )
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
            )
            glob.player.queue += packets.notification(
                'Mode was switched to vanilla!'
            )
            asyncio.create_task(glob.player.update(glob.mode))

    if glob.config.osu_api_key:
        lb = await Leaderboard.from_bancho(parsed_params)
    else:
        lb = await Leaderboard.from_offline(parsed_params)

    valid_bmap = lb.bmap and lb.bmap.approved in (1, 2, 3, 4)
    if not valid_bmap and not glob.config.disable_funorange_maps:
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
            lb = await ModifiedLeaderboard.from_client(parsed_params)
            log_success(f'handled funorange map of {filename}')
        else:
            log_success(f'handled bancho(?) map of {filename}')
    else:
        log_success(f'handled map of setid: {setid}')

    return Response(200, lb.as_binary)

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
    -1: '',
    0: 'std',
    1: 'taiko',
    2: 'ctb',
    3: 'mania'
}

COMMAND_NOT_FOUND = DirectResponse.from_str(
    'command not found!'
).as_binary

convert_param_mode_to_api = lambda x: DIRECT_TO_MIRROR_MODE[x]
convert_param_rankstatus_to_api = lambda x: DIRECT_TO_API_STATUS[x]

@web.get('/osu-search.php')
async def direct(
    query: str = Query(urlparse.unquote_plus, Alias('q')),
    mode: str = Query(convert_param_mode_to_api, Alias('m')),
    ranking_status: str = Query(convert_param_rankstatus_to_api, Alias('r'))
) -> Response:
    if query.startswith(glob.config.command_prefix):
        query_no_prefix = query.removeprefix(glob.config.command_prefix)
        split = query_no_prefix.split()
        
        if (
            not split or
            split[0] not in glob.commands
        ):
            return Response(200, COMMAND_NOT_FOUND)
        
        cmd, *args = split

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

    if not glob.config.bancho_username or not glob.config.bancho_pw_md5:
        utils.add_to_player_queue(
            packets.notification("No username/password provided for direct!")
        )
        return Response(200, b'0')

    args: dict[str, Union[int, str]] = {
        'u': glob.config.osu_username,
        'h': glob.config.osu_password
    }

    if query not in ("Newest", "Top Rated", "Most Played"):
        args['q'] = query

    if mode != -1:
        args['m'] = mode

    args['s'] = ranking_status

    try:
        async with glob.http.get(
            url = 'https://osu.ppy.sh/web/osu-search.php',
            params = args
        ) as resp:
            ret = await resp.read()
    except aiohttp.ClientConnectorError:
        log_error('mirror currently down')
        return Response(200, b'0')
    
    log_success(f'maps loaded for query: `{query}` !')
    return Response(
        code = 200, 
        body = ret
    )
