from dataclasses import dataclass
from core.models.domain.normalizers.mods import Mods
from core.models.domain.normalizers.rank_status import RankStatus
from ossapi import Beatmap, Beatmapset, Score, UserCompact
from core.models.domain.normalizers.game_mode import GameMode


@dataclass
class OsuApiBeatmap:
    id: int
    set_id: int
    md5: str
    artist: str
    title: str
    difficulty_name: str
    max_combo: int
    status: RankStatus
    mode: GameMode
    play_count: int
    pass_count: int
    last_updated: int
    average_rating: float

    @classmethod
    def from_api(cls, beatmap: Beatmap, beatmap_set: Beatmapset) -> "OsuApiBeatmap":
        assert beatmap.checksum, "Beatmap checksum is required to create OsuApiBeatmap"

        return cls(
            id=beatmap.id,
            set_id=beatmap_set.id,
            md5=beatmap.checksum,
            artist=beatmap_set.artist,
            title=beatmap_set.title,
            difficulty_name=beatmap.version,
            max_combo=beatmap.max_combo or 0,
            status=RankStatus.from_api(beatmap.status),
            mode=GameMode.from_api(beatmap.mode),
            play_count=beatmap.playcount,
            pass_count=beatmap.passcount,
            last_updated=int(beatmap.last_updated.timestamp()),
            average_rating=beatmap.rating,
        )


@dataclass
class OsuApiScore:
    id: int | None
    user_id: int
    user_name: str

    game_mode: GameMode

    total_score_v1: int | None
    total_score_v2: int | None

    combo: int
    beatmap_max_combo: int

    count_50: int
    count_100: int
    count_300: int
    count_miss: int
    perfect: bool

    mods: Mods

    time_set: int
    replay_available: bool

    pp: int
    lazer: bool

    @classmethod
    def from_api(
        cls,
        score: "Score",
        game_mode: GameMode
    ) -> "OsuApiScore":
        assert score.beatmap, "Score's beatmap is required to create OsuApiScore"
        assert score.beatmap.max_combo is not None, "Score's beatmap max combo is required to create OsuApiScore"

        user: UserCompact = score._ossapi_data["_user"]

        if not score.legacy_score_id:
            lazer = True
        else:
            lazer = False

        if score.pp:
            pp = int(score.pp)
        else:
            pp = 0

        score_id = (
            score.legacy_score_id or
            score.id or
            None
        )

        valid_replay_avaliable = (
            score.replay and
            not lazer and
            score_id
        )

        if valid_replay_avaliable:
            replay_available = True
        else:
            replay_available = False

        return cls(
            id=score_id,
            user_id=score.user_id,
            user_name=user.username,
            game_mode=game_mode,
            total_score_v1=score.classic_total_score,
            total_score_v2=score.total_score,
            combo=score.max_combo,
            beatmap_max_combo=score.beatmap.max_combo,
            count_50=score.statistics.meh or 0,
            count_100=score.statistics.ok or 0,
            count_300=score.statistics.great or 0,
            count_miss=score.statistics.miss or 0,
            perfect=score.is_perfect_combo,
            mods=Mods.from_api(score.mods),
            time_set=int(score.ended_at.timestamp()),
            replay_available=replay_available,
            pp=pp,
            lazer=lazer
        )
