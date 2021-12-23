import utils
import orjson
import queries
import asyncio
from ext import glob
from utils import log
from utils import Color
from objects import Mods
from utils import handler
from objects import Score
from server import Request
from objects import Player
from server import Response
from objects import Beatmap
from typing import Optional
from objects import ModifiedBeatmap

JSON = orjson.dumps

@handler(
    ('/api/v1/client/tops', '/api/v1/client/recalc', # type: ignore
    '/api/v1/client/recent', '/api/v1/client/profile', # type: ignore
    '/api/v1/client/wipe') # type: ignore
)
async def client_handlers(request: Request) -> Response:
    path = request.path.replace('/client', '')

    if glob.player:
        request.params['u'] = glob.player.name
        log(
            f'handling {path.split("/")[-1]} button for client',
            color = Color.GREEN
        )

    return await glob.handlers[path](request)

@handler('/api/v1/profile')
async def profile(request: Request) -> Response:
    if (
        not (params := request.params) or
        'u' not in params
    ):
        return Response(
            code = 200,
            body = JSON({
                'status': 'failed',
                'message': (
                    'please provide a profile name in parameters\n'
                    'example: http://127.0.0.1:5000/api/v1/client/profile?u=profile name'
                )
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    p = Player(params['u'])

    filter_mod = None
    m = 'vn'
    if 'm' in params:
        m = params['m'].lower().strip()
        if m == 'rx':
            filter_mod = Mods.RELAX
        elif m == 'ap':
            filter_mod = Mods.AUTOPILOT
        else:
            m = 'vn'
            filter_mod = None

    await p.update(filter_mod)

    response_json = {
        'status': 'success!',
        'name': p.name,
        'rank': p.rank,
        'playcount': p.playcount,
        'pp': p.pp,
        'mode': m
    }

    return Response(
        code = 200,
        body = JSON(response_json),
        headers = {'Content-type': 'application/json charset=utf-8'}
    )

SCORES = list[dict]
RANKED_PLAYS = dict[str, list[dict]]
APPROVED_PLAYS = RANKED_PLAYS
@handler('/api/v1/tops')
async def tops(request: Request) -> Response:
    if (
        not (params := request.params) or
        'u' not in params
    ):
        return Response(
            code = 200,
            body = JSON({
                'status': 'failed',
                'message': (
                    'please provide a profile name in parameters\n'
                    'example: http://127.0.0.1:5000/api/v1/client/tops?u=profile name'
                )
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    if 'limit' not in params:
        limit = 100
    else:
        limit = params['limit']

    if 'm' not in params:
        filter_mod = None
    else:
        filter_mod = Mods.from_str(params['m'])

    name: str = params['u']
    if name not in glob.profiles:
        Response(
            code = 200,
            body = JSON({
                'status': 'failed',
                'message': "profile can't be found!"
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    profile = glob.profiles[name]
    response_json = {
        'status': 'success!',
        'name': name,
        'mode': 'unknown' if 'm' not in params else params['m'],
        'plays': []
    }

    scores: SCORES = []

    ranked_plays: Optional[RANKED_PLAYS] = \
    profile['plays']['ranked_plays']

    approved_plays: Optional[APPROVED_PLAYS] = \
    profile['plays']['approved_plays']

    for plays in (ranked_plays, approved_plays):
        if plays:
            for v in plays.values():
                scores.extend(v)

    if filter_mod:
        scores = [
            x for x in scores if
            x['mods'] & filter_mod
        ]
    else:
        scores = [
            x for x in scores if
            not x['mods'] & (Mods.RELAX | Mods.AUTOPILOT)
        ]

    scores.sort(key = lambda s: s['pp'], reverse = True)
    top_scores = utils.filter_top_scores(scores[:limit])
    top_scores.sort(key = lambda s: s['pp'], reverse = True)

    for play in top_scores.copy():
        bmap = (
            await ModifiedBeatmap.from_md5(play['md5']) or
            await Beatmap.from_md5(play['md5'])
        )

        if (
            'mods_str' not in play or
            play['mods_str'] is None
        ):
            play['mods_str'] = repr(Mods(play['mods']))

        if bmap:
            bmap_dict = bmap.as_dict()
            try: del bmap_dict['file_content']
            except: pass

            play['bmap'] = bmap_dict
        else:
            play['bmap'] = None

        try: del play['replay_frames']
        except: pass

        response_json['plays'].append(play)

    return Response(
        code = 200,
        body = JSON(response_json),
        headers = {'Content-type': 'application/json charset=utf-8'}
    )

@handler('/api/v1/recent')
async def recent(request: Request) -> Response:
    if (
        not (params := request.params) or
        'u' not in params
    ):
        return Response(
            code = 200,
            body = JSON({
                'status': 'failed',
                'message': (
                    'please provide a profile name in parameters\n'
                    'example: http://127.0.0.1:5000/api/v1/client/recent?u=profile name'
                )
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    name: str = params['u']
    if name not in glob.profiles:
        Response(
            code = 200,
            body = JSON({
                'status': 'failed',
                'message': "profile can't be found!"
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    if 'limit' not in params:
        limit = 100
    else:
        limit = params['limit']

    if 'm' not in params:
        filter_mod = None
    else:
        filter_mod = Mods.from_str(params['m'])

    profile = glob.profiles[name]
    response_json = {
        'status': 'success!',
        'name': name,
        'mode': 'unknown' if 'm' not in params else params['m'],
        'plays': []
    }

    scores: Optional[SCORES] = \
    profile['plays']['all_plays']

    if not scores:
        scores = []

    if filter_mod:
        scores = [
            x for x in scores if
            x['mods'] & filter_mod
        ]
    else:
        scores = [
            x for x in scores if
            not x['mods'] & (Mods.RELAX | Mods.AUTOPILOT)
        ]

    scores.sort(
        key = lambda s: s['time']
        if 'time' in s else 0,
        reverse = True
    )

    for play in scores[:limit].copy():
        bmap = (
            await ModifiedBeatmap.from_md5(play['md5']) or
            await Beatmap.from_md5(play['md5'])
        )

        if (
            'mods_str' not in play or
            play['mods_str'] is None
        ):
            play['mods_str'] = repr(Mods(play['mods']))

        if bmap:
            bmap_dict = bmap.as_dict()
            try: del bmap_dict['file_content']
            except: pass

            play['bmap'] = bmap_dict
        else:
            play['bmap'] = None

        try: del play['replay_frames']
        except: pass

        response_json['plays'].append(play)

    return Response(
        code = 200,
        body = JSON(response_json),
        headers = {'Content-type': 'application/json charset=utf-8'}
    )

async def _recalc(md5: str, score: Score) -> dict:
    bmap = (
        await ModifiedBeatmap.from_md5(md5) or
        await Beatmap.from_md5(md5)
    )

    if (
        not bmap or
        not await bmap.get_file()
    ):
        score.pp = 0.0
        return score.as_dict()

    pp, acc = utils.calculator(score, bmap)

    score.pp = pp
    score.acc = acc
    return score.as_dict()

ACCEPTED_PLAYS = ('ranked_plays', 'approved_plays')
@handler('/api/v1/recalc')
async def recalc(request: Request) -> Response:
    # TODO: make use of the params

    async def background_recalc() -> None:
        profiles = glob.profiles
        for index_of_profile, profile_name in enumerate(profiles):
            log(
                f'{index_of_profile}/{len(profiles)}', 'profiles calculated.',
                color = Color.LIGHTMAGENTA_EX
            )

            profile = profiles[profile_name]

            for index_of_type_plays, map_status in enumerate(ACCEPTED_PLAYS):
                msg = (
                    f"calculating {map_status[:-6]} maps of {profile_name}\n"
                    f'{index_of_type_plays + 1}/2 calculated.'
                )

                log(msg, color = Color.LIGHTMAGENTA_EX)
                plays: dict[str, list[dict]] = profile['plays'][map_status]

                for index_of_maps, (md5, map_plays) in enumerate(plays.items()):
                    for idx, play in enumerate(map_plays):
                        map_plays[idx] = await _recalc(
                            md5 = md5,
                            score = Score.from_dict(
                                play, ignore_binascii_errors = True
                            )
                        )

                        log(
                            f'{idx+1}/{len(map_plays)}',
                            'plays in this map calculated.',
                            color = Color.LIGHTMAGENTA_EX
                        )

                    log(
                        f'{index_of_maps + 1}/{len(plays.values())}',
                        'maps calculated.', color = Color.LIGHTMAGENTA_EX
                    )

        log('finished recalcing!', color = Color.LIGHTMAGENTA_EX)
        utils.update_files()

    asyncio.create_task(background_recalc())

    response_msg = {
        'status': 'success!',
        'message': 'All profiles are being calculated!'
    }
    return Response(
        code = 200,
        body = JSON(response_msg),
        headers = {'Content-type': 'application/json charset=utf-8'}
    )

@handler('/api/v1/wipe')
async def wipe_profile(request: Request) -> Response:
    if (
        not (params := request.params) or
        'u' not in params
    ):
        return Response(
            code = 200,
            body = JSON({
                'status': 'failed',
                'message': (
                    'please provide a profile name in parameters\n'
                    'example: http://127.0.0.1:5000/api/v1/wipe?u=profile name'
                )
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    if 'yes' not in params:
        return Response(
            code = 200,
            body = JSON({
                'status': '1/2 done',
                'message': (
                    'CURRENTLY IT WILL WIPE ALL YOUR STATS INCLUDING RX, AP, VN ON\n'
                    'YOUR CURRENT PROFILE YOU ARE TRYING TO WIPE\n'
                    'TODO: check and wipe for different modes\n'
                    'if you are sure you want to wipe\n'
                    'type the following at the end of the url and click enter\n'
                    '&yes=yes'
                )
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    if params['yes'] != 'yes':
        return Response(
            code = 200,
            body = JSON({
                'status': 'fail',
                'message': "yes didn't equal yes!"
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    name: str = params['u']
    if name not in glob.profiles:
        Response(
            code = 200,
            body = JSON({
                'status': 'failed',
                'message': "profile can't be found!"
            }),
            headers = {'Content-type': 'application/json charset=utf-8'}
        )

    glob.profiles.update(
        queries.init_profile(name)
    )

    utils.update_files()

    if (
        glob.player and
        glob.player.name == name
    ):
        await glob.player.update(glob.mode)

    response_msg = {
        'status': 'success!',
        'message': f'{name} was wiped!'
    }
    return Response(
        code = 200,
        body = JSON(response_msg),
        headers = {'Content-type': 'application/json charset=utf-8'}
    )