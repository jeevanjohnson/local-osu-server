from core.models.domain.gameplay.mods import Mods
from core.models.domain.gameplay.game_mode import GameMode
from ossapi.models import Score
from dataclasses import dataclass

@dataclass
class BanchoScore:
    score_id: int
    username: str
    combo: int
    count50: int
    count100: int
    count300: int
    count_miss: int
    perfect: bool
    mods: Mods
    user_id: int
    time_set: int
    replay_available: bool
    pp: int
    game_mode: GameMode
    lazer: bool

    score_override: int | None = None

def from_api_to_bancho_score(score: Score, mode: GameMode) -> BanchoScore:
    mods = Mods.from_api_v2(score.mods)

    lazer = not score.legacy_score_id

    user = score.user()

    if score.pp:
        pp = int(score.pp)
    else:
        pp = 0
    
    if not lazer:
        score_override = score.legacy_total_score
    else:        
        score_override = None

    return BanchoScore(
        score_id=score.id or 0,
        username=user.username,
        combo=score.max_combo,
        count50=score.statistics.meh or 0,
        count100=score.statistics.ok or 0,
        count300=score.statistics.great or 0,
        count_miss=score.statistics.miss or 0,
        perfect=score.is_perfect_combo,
        mods=mods,
        user_id=user.id,
        time_set=int(score.ended_at.timestamp()),
        replay_available=score.has_replay,
        pp=pp,
        game_mode=mode,
        lazer=lazer,
        score_override=score_override,
    )