import utils
import packets
from ext import glob
from utils import log
from utils import Color
from objects import Mods
from objects import Score
from objects import Beatmap
from typing import Optional
from objects import ModifiedBeatmap

RANKED_PLAYS = dict[str, list[dict]]

SCORE = list[dict]

leaderboard_worthy = (1, 2, 3, 4)
status_to_db = {
    1: 'ranked',
    2: 'approved',
    3: 'qualified',
    4: 'loved'
}

async def score_submit(score: Score) -> None:
    if not glob.player:
        return

    if score.name != glob.player.name:
        glob.player.queue += packets.notification(
            "Can't submit another person's replay!"
        )
        return

    if (
        score.replay_md5 in
        glob.current_profile['plays']['replay_md5']
    ):
        glob.player.queue += packets.notification(
            "Can't submit the same replay!"
        )
        return

    # if cinema, autopilot, cinema, or relax in mods
    if score.mods & glob.invalid_mods:
        glob.player.queue += packets.notification(
            "Invalid mods to submit!"
        )
        return

    if score.is_failed:
        glob.player.queue += packets.notification(
            "Can't submit failed replays!"
        )
        return

    if score.mode != 0:
        glob.player.queue += packets.notification(
            "Must be a standard score!"
        )
        return

    if glob.config.disable_funorange_maps:
        bmap = await Beatmap.from_md5(score.md5)
    else:
        bmap = (
            await ModifiedBeatmap.from_md5(score.md5) or
            await Beatmap.from_md5(score.md5)
        )
    
    if not bmap:
        glob.player.queue += packets.notification("Map has to exist on bancho!")
        return

    if bmap.approved not in leaderboard_worthy:
        glob.player.queue += packets.notification("Map can't be unranked!")
        return

    if not await bmap.get_file():
        glob.player.queue += packets.notification(
            "Can't seem to get .osu file for this map!"
        )
        return

    if not bmap.in_db:
        bmap.add_to_db() # type: ignore

    pp, acc_percent = utils.calculator(score, bmap)
    score.acc = acc_percent
    score.bmap = bmap
    score.pp = pp

    score.mods_str = repr(Mods(score.mods))

    all_plays: Optional[SCORE] = \
    glob.current_profile['plays']['all_plays']

    if all_plays is None:
        return

    score.scoreid = len(all_plays) + 1

    score_dict = score.as_dict()
    all_plays.append(score_dict)

    key = f'{status_to_db[bmap.approved]}_plays'

    type_plays: Optional[dict[str, list[dict]]] = \
    glob.current_profile['plays'][key]

    if type_plays is None:
        return

    if score.md5 not in type_plays:
        type_plays[score.md5] = [score_dict]
    else:
        type_plays[score.md5].append(score_dict)

    replay_md5s: Optional[list[str]] = \
    glob.current_profile['plays']['replay_md5']

    if replay_md5s is None:
        return

    if score.replay_md5:
        replay_md5s.append(score.replay_md5)

    utils.update_files()
    await glob.player.update(glob.mode)

    score_str = (
        f'{bmap.artist} - {bmap.title} [{bmap.version}]\n'
        f'+{score.mods_str} {score.acc:.2f}%\n'
        f'{utils.get_grade(score)} {score.pp:.0f}PP {score.nmiss}x\n'
        f'was successfully submitted!'
    )

    glob.player.queue += packets.notification(score_str)

    """Sends score to recent channel"""
    msg = (
        f'{bmap.artist} - {bmap.title} [{bmap.version}]\n'
        f'+{score.mods_str} {score.acc:.2f}% {utils.get_grade(score)} {score.pp:.0f}PP '
        f'{score.max_combo}x/{bmap.max_combo}x {score.nmiss}X'
    )
    if glob.config.ping_user_when_recent_score:
        msg += f'\nachieved by {glob.player.name}'

    glob.player.queue += utils.local_message(msg, channel='#recent')
    log(glob.player.name, 'has successfully submitted a score!', color = Color.GREEN)