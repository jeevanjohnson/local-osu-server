import utils
import orjson
import queries
import asyncio
from ext import glob
from utils import log
from utils import Color
from objects import Mods
from server import Alias
from server import Query
from objects import Score
from server import Router
from objects import Player
from objects import Beatmap
from typing import Optional
import urllib.parse as urlparse
from objects import ModifiedBeatmap
from server import SuccessJsonResponse

api = Router('/api/v1')

lower = lambda x: x.lower()
JSON = orjson.dumps

@api.get('/profile')
async def profile(
    name: str = Query(urlparse.unquote_plus, Alias('u')),
    mode: str = Query(lower, Alias('m'))
) -> SuccessJsonResponse:
    p = Player(name)

    filter_mod = None
    
    if mode == 'rx':
        filter_mod = Mods.RELAX
    elif mode == 'ap':
        filter_mod = Mods.AUTOPILOT
    else:
        mode = 'vn'
        filter_mod = None

    await p.update(filter_mod)

    response_json = {
        'status': 'success!',
        'name': p.name,
        'rank': p.rank,
        'playcount': p.playcount,
        'pp': p.pp,
        'acc': p.acc,
        'mode': mode,
    }

    return SuccessJsonResponse(response_json)

SCORES = list[dict]
RANKED_PLAYS = dict[str, list[dict]]
APPROVED_PLAYS = RANKED_PLAYS

@api.get('/tops')
async def tops(
    name: str = Query(urlparse.unquote_plus, Alias('u')),
    limit: int = 100,
    mode: str = Query(lower, Alias('m')),
) -> SuccessJsonResponse:

    if mode != 'vn':
        filter_mod = Mods.from_str(mode)
    else:
        filter_mod = None

    if name not in glob.profiles:
        return SuccessJsonResponse({
            'status': 'failed',
            'message': "profile can't be found!"
        })

    profile = glob.profiles[name]
    response_json = {
        'status': 'success!',
        'name': name,
        'mode': 'vn' if not filter_mod else mode,
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
    
    if glob.config.disable_funorange_maps:
        scores = [
            x for x in scores if 
            x['md5'] not in glob.modified_beatmaps
        ]

    scores.sort(key = lambda s: s['pp'], reverse = True)
    top_scores = utils.filter_top_scores(scores[:limit])
    top_scores.sort(key = lambda s: s['pp'], reverse = True)

    for play in top_scores.copy():
        bmap = (
            await ModifiedBeatmap.from_md5(play['md5']) or
            await Beatmap.from_md5(play['md5'])
        )
        
        if bmap:
            bmap_dict = utils.delete_keys(
                bmap.as_dict(), 'file_content'
            )

            play['bmap'] = bmap_dict
        else:
            continue
        
        if (
            'mods_str' not in play or
            not play['mods_str']
        ):
            play['mods_str'] = repr(Mods(play['mods']))

        play = utils.delete_keys(
            play, 'replay_frames'
        )

        response_json['plays'].append(play)

    return SuccessJsonResponse(response_json)

@api.get('/recent')
async def recent(
    name: str = Query(urlparse.unquote_plus, Alias('u')),
    limit: int = 100,
    mode: str = Query(lower, Alias('m')),
) -> SuccessJsonResponse:

    if name not in glob.profiles:
        return SuccessJsonResponse({
            'status': 'failed',
            'message': "profile can't be found!"
        })

    if mode != 'vn':
        filter_mod = Mods.from_str(mode)
    else:
        filter_mod = None

    profile = glob.profiles[name]
    response_json = {
        'status': 'success!',
        'name': name,
        'mode': 'vn' if not filter_mod else mode,
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

    if glob.config.disable_funorange_maps:
        scores = [
            x for x in scores if 
            x['md5'] not in glob.modified_beatmaps
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
            not play['mods_str']
        ):
            play['mods_str'] = repr(Mods(play['mods']))

        if bmap:
            bmap_dict = utils.delete_keys(
                bmap.as_dict(), 'file_content'
            )

            play['bmap'] = bmap_dict
        else:
            play['bmap'] = None

        play = utils.delete_keys(
            play, 'replay_frames'
        )

        response_json['plays'].append(play)

    return SuccessJsonResponse(response_json)

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
@api.get('/recalc')
async def recalc(
    name: str = Query(urlparse.unquote_plus, Alias('u'))
) -> SuccessJsonResponse:
    
    if (
        name != 'all' and 
        name not in glob.profiles
    ):
        return SuccessJsonResponse({
            'status': 'fail',
            'message': 'invalid name'
        })

    async def background_recalc() -> None:
        if name == 'all':
            profiles = glob.profiles
        else:
            profiles = [glob.profiles[name]]
        
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

    return SuccessJsonResponse({
        'status': 'success!',
        'message': 'All profiles are being calculated!'
    })

@api.get('/api/v1/wipe')
async def wipe_profile(
    name: str = Query(urlparse.unquote_plus, Alias('u')),
    yes: str = ''
) -> SuccessJsonResponse:

    if not yes:
        return SuccessJsonResponse({
            'status': '1/2 done',
            'message': (
                'CURRENTLY IT WILL WIPE ALL YOUR STATS INCLUDING RX, AP, VN ON\n'
                'YOUR CURRENT PROFILE YOU ARE TRYING TO WIPE\n'
                'TODO: check and wipe for different modes\n'
                'if you are sure you want to wipe\n'
                'type the following at the end of the url and click enter\n'
                '&yes=yes'
            )
        })

    if yes != 'yes':
        return SuccessJsonResponse({
            'status': 'fail',
            'message': "yes didn't equal yes!"
        })

    if name not in glob.profiles:
        return SuccessJsonResponse({
            'status': 'failed',
            'message': "profile can't be found!"
        })

    glob.profiles.update(
        queries.init_profile(name)
    )

    utils.update_files()

    if (
        glob.player and
        glob.player.name == name
    ):
        await glob.player.update(glob.mode)

    return SuccessJsonResponse({
        'status': 'success!',
        'message': f'{name} was wiped!'
    })