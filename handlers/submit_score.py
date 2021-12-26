import utils
import config
import packets
from ext import glob
from utils import log
from utils import Color
from objects import Mods
from utils import handler
from objects import Score
from objects import Beatmap
from typing import Optional
from objects import ModifiedBeatmap

RANKED_PLAYS = dict[str, list[dict]]

def get_grade(score: Score) -> str:
    total = score.n300 + score.n100 + score.n50 + score.nmiss
    n300_percent = score.n300 / total
    using_hdfl = score.mods & 1032
    nomiss = score.nmiss == 0

    if n300_percent > 0.9:
        if nomiss and (score.n50 / total) < 0.1:
            return 'SH' if using_hdfl else 'S'
        else:
            return 'A'

    if n300_percent > 0.8:
        return 'A' if nomiss else 'B'

    if n300_percent > 0.7:
        return 'B' if nomiss else 'C'

    if n300_percent > 0.6:
        return 'C'

    return 'D'

SCORE = list[dict]

leaderboard_worthy = (1, 2, 3, 4)
status_to_db = {
    1: 'ranked',
    2: 'approved',
    3: 'qualified',
    4: 'loved'
}
@handler('score_sub')
async def submit_score() -> None:
    if not glob.player:
        return

    if not glob.current_profile:
        return

    score = Score.from_score_sub()
    if not score:
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

    if config.disable_funorange_maps:
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
        f'{get_grade(score)} {score.pp:.0f}PP {score.nmiss}x\n'
        f'was successfully submitted!'
    )

    glob.player.queue += packets.notification(score_str)

    """Sends score to recent channel"""
    msg = (
        f'{bmap.artist} - {bmap.title} [{bmap.version}]\n'
        f'+{score.mods_str} {score.acc:.2f}% {get_grade(score)} {score.pp:.0f}PP '
        f'{score.max_combo}x/{bmap.max_combo}x {score.nmiss}X'
    )
    if config.ping_user_when_recent_score:
        msg += f'\nachieved by {glob.player.name}'

    glob.player.queue += packets.sendMsg(
        client = 'local',
        msg = msg,
        target = '#recent',
        userid = -1,
    )

    log(glob.player.name, 'has successfully submitted a score!', color = Color.GREEN)