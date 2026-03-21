from enum import IntEnum
from enum import unique
from dataclasses import dataclass

import ossapi.enums

from osuProtocol.server_packets import osuMods
import ossapi.enums
from models.bancho.scores import Score, LazerScore, StableScore

@unique
class osuMapStatus(IntEnum):
    """
    Represents the ranked status of a beatmap.
    """
    NOTSUBMITTED = -1
    PENDING = 0
    UPDATEAVALIABLE = 1
    RANKED = 2
    APPROVED = 3
    QUALIFIED = 4
    LOVED = 5

    @classmethod
    def from_api_v2(cls, ranked_status: ossapi.enums.RankStatus) -> 'osuMapStatus':
        return {
            ossapi.enums.RankStatus.GRAVEYARD: cls.PENDING,
            ossapi.enums.RankStatus.WIP: cls.PENDING,
            ossapi.enums.RankStatus.PENDING: cls.PENDING,
            ossapi.enums.RankStatus.RANKED: cls.RANKED,
            ossapi.enums.RankStatus.APPROVED: cls.APPROVED,
            ossapi.enums.RankStatus.QUALIFIED: cls.QUALIFIED,
            ossapi.enums.RankStatus.LOVED: cls.LOVED,
        }[ranked_status]
        
@unique
class LeaderboardType(IntEnum):
    """
    Types of leaderboards that can be requested.
    """
    LOCAL   = 0
    TOP     = 1
    MODS    = 2
    FRIENDS = 3
    COUNTRY = 4

LEADERBOARD_SCORE_FMT = (
    "{id}|{name}|{score}|{max_combo}|"
    "{n50}|{n100}|{n300}|{nmiss}|{nkatu}|{ngeki}|"
    "{perfect}|{mods}|{userid}|{rank}|{time}|{has_replay}"
)

EpochTime = int

@dataclass
class LeaderboardScore:
    """
    Represents a single score on the leaderboard.
    """
    score_id: int
    username: str
    score: int
    max_combo: int
    count50: int
    count100: int
    count300: int
    count_miss: int
    countkatu: int
    countgeki: int
    perfect: bool
    enabled_mods: osuMods
    user_id: int
    position: int
    time_set: EpochTime
    replay_available: bool

    def serialize(self) -> str:
        return LEADERBOARD_SCORE_FMT.format(
            id=self.score_id,
            name=self.username,
            score=self.score,
            max_combo=self.max_combo,
            n50=self.count50,
            n100=self.count100,
            n300=self.count300,
            nmiss=self.count_miss,
            nkatu=self.countkatu,
            ngeki=self.countgeki,
            perfect=int(self.perfect),
            mods=self.enabled_mods,
            userid=self.user_id,
            rank=self.position,
            time=self.time_set,
            has_replay=int(self.replay_available)
        )

    def __repr__(self) -> str:
        return self.serialize()

    @classmethod
    def from_score(
        cls, 
        score: Score, 
        position: int,
        ingame_score: int,
        from_difficulty_adjusted: bool = False
    ) -> 'LeaderboardScore':
        stable_mods, lazer_mods = score.enabled_mods.to_stable_mods()

        if isinstance(score, LazerScore):
            title = f"[LAZER] {score.username}"

            total_lazer_mods = len(lazer_mods)

            if lazer_mods:
                title += " ("
                
                for i, lazer_mod in enumerate(lazer_mods):
                    if lazer_mod == "DA":
                        continue

                    if i == total_lazer_mods - 1:
                        title += lazer_mod
                    else:
                        title += lazer_mod + ","
                
                title += ")"
        else:
            title = score.username

        if from_difficulty_adjusted:
            # https://capitalizemytitle.com/small-text-converter/
            title = f"[ᵒᵍ ᵈⁱᶠᶠ] {title}"
            
            if "DT" in score.enabled_mods or "NC" in score.enabled_mods:
                title += " (1.5x)"
            elif "HT" in score.enabled_mods or "DC" in score.enabled_mods:
                title += " (0.75x)"
            else:
                title += " (1x)"

            # if not score.lazer or "DA" not in score.enabled_mods:
            #     title += " (base diff)"
        
        return cls(
            score_id=score.score_id,
            username=title,
            score=ingame_score,
            max_combo=score.combo.actual,
            count50=score.count50,
            count100=score.count100,
            count300=score.count300,
            count_miss=score.count_miss,
            countkatu=0,
            countgeki=0,
            perfect=score.perfect,
            enabled_mods=stable_mods, 
            user_id=score.user_id,
            position=position,
            time_set=score.time_set,
            replay_available=score.replay_available
        )

STARTING_LB_FORMAT = (
    "{beatmap_status}|false|{beatmap_id}|{beatmap_set_id}|{num_of_scores}\n0\n"
    "[bold:0,size:20]{artist_unicode}|{title_unicode}\n10.0\n"
)

@dataclass
class LeaderboardHeader:
    """
    Represents the header of a leaderboard, containing metadata about the leaderboard.
    """
    beatmap_status: osuMapStatus
    beatmap_id: int
    beatmap_set_id: int
    num_of_scores: int
    artist: str
    title: str

    def serialize(self) -> str:
        return STARTING_LB_FORMAT.format(
            beatmap_status=self.beatmap_status.value,
            beatmap_id=self.beatmap_id,
            beatmap_set_id=self.beatmap_set_id,
            num_of_scores=self.num_of_scores,
            artist_unicode=self.artist,
            title_unicode=self.title
        )
    
class Leaderboard:
    """
    Represents a full leaderboard, including the header and the list of scores.
    """
    def __init__(
            self, 
            header: LeaderboardHeader, 
            scores: list[LeaderboardScore] | None = None,
            personal_best: LeaderboardScore | None = None
        ):
        self.header = header

        if scores is None:
            self.scores = []
        else:
            self.scores = scores
        
        self.personal_best = personal_best
    
    def update_scores(self, new_scores: list[LeaderboardScore]):
        self.scores = new_scores

    def serialize(self) -> bytes:
        if isinstance(self.header.beatmap_status, bool):
            error_message = (
                f"Error: Beatmap status is a boolean value ({self.header.beatmap_status}). This is likely a bug.\n"
                f"Beatmap ID: {self.header.beatmap_id}, Beatmap Set ID: {self.header.beatmap_set_id}\n"
                f"Artist: {self.header.artist}, Title: {self.header.title}"
            )
            raise ValueError(error_message)

        if self.header.beatmap_status < 1:
            return f'{self.header.beatmap_status.value}|false'.encode()
        
        buffer = bytearray()

        buffer += self.header.serialize().encode()

        raw_personal_best = b'\n'
        if self.personal_best:
            raw_personal_best = self.personal_best.serialize().encode() + b'\n'
        
        buffer += raw_personal_best

        for score in self.scores:
            buffer += score.serialize().encode() + b'\n'

        return bytes(buffer)
    
class GraveyardLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that are in the graveyard.
    """
    def __init__(self):
        super().__init__(LeaderboardHeader(
            beatmap_status=osuMapStatus.PENDING,
            beatmap_id=0,
            beatmap_set_id=0,
            num_of_scores=0,
            artist="",
            title=""
        ), [])

# class UpdatedBeatmapLeaderboard(Leaderboard):
#     """
#     Represents a leaderboard for beatmaps that have been updated.
#     """
#     def __init__(self, beatmap_id: int, beatmap_set_id: int, artist: str, title: str):
#         super().__init__(LeaderboardHeader(
#             beatmap_status=osuMapStatus.UPDATEAVALIABLE,
#             beatmap_id=beatmap_id,
#             beatmap_set_id=beatmap_set_id,
#             num_of_scores=0,
#             artist=artist,
#             title=title
#         ), [])

class ScoringAlgorithm(IntEnum):
    LAZER = 0
    PP = 1

    def to_api_v2(self) -> ossapi.enums.RankingType:
        return {
            ScoringAlgorithm.LAZER: ossapi.enums.RankingType.SCORE,
            ScoringAlgorithm.PP: ossapi.enums.RankingType.PERFORMANCE
        }[self]