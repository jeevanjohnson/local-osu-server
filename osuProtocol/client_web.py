from enum import IntEnum
from enum import unique
from dataclasses import dataclass

from osuProtocol.server_packets import osuMods
from ossapi.enums import RankStatus

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
    def from_api_v2_ranked_status(cls, ranked_status: RankStatus) -> 'osuMapStatus':
        return {
            RankStatus.GRAVEYARD: cls.PENDING,
            RankStatus.WIP: cls.PENDING,
            RankStatus.PENDING: cls.PENDING,
            RankStatus.RANKED: cls.RANKED,
            RankStatus.APPROVED: cls.APPROVED,
            RankStatus.QUALIFIED: cls.QUALIFIED,
            RankStatus.LOVED: cls.LOVED,
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
    def from_score(cls, score: 'Score', position: int) -> 'LeaderboardScore':
        if isinstance(score, LazerScore):
            mods = osuMods.NOMOD

            for mod_str in score.enabled_mods:
                try:
                    mod_enum = osuMods.from_mod_string(mod_str)
                    mods |= mod_enum
                except (KeyError, ValueError):
                    # Handle unknown mod strings gracefully
                    print(f"Warning: Unknown mod '{mod_str}' in score {score.score_id}")
        else:
            mods = score.enabled_mods
        
        if isinstance(score, LegacyScore):
            total_score = score.lazer_score()
        else:
            total_score = score.total_score
        
        return cls(
            score_id=score.score_id,
            username=score.title,
            score=total_score,
            max_combo=score.max_combo,
            count50=score.count50,
            count100=score.count100,
            count300=score.count300,
            count_miss=score.count_miss,
            countkatu=0,  # TODO: Implement katu/geki counts, probably wont need to since stable works just fine without them
            countgeki=0,  # TODO: Implement katu/geki counts, probably wont need to since stable works just fine without them
            perfect=score.perfect,
            enabled_mods=mods,  # Handle lazer scores with list[str] mods
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
            beatmap_status=osuMapStatus.NOTSUBMITTED,
            beatmap_id=0,
            beatmap_set_id=0,
            num_of_scores=0,
            artist="",
            title=""
        ), [])

@dataclass
class Score:
    score_id: int
    username: str
    total_score: int
    max_combo: int
    count50: int
    count100: int
    count300: int
    count_miss: int
    perfect: bool
    enabled_mods: osuMods
    user_id: int
    time_set: EpochTime
    replay_available: bool
    pp: int | None
    beatmap_max_combo: int

    @property
    def title(self) -> str:
        raise NotImplementedError("Subclasses must implement the title property")

def seperate_lazer_and_stable_mods(mod_strings: list[str]) -> tuple[osuMods, list[str]]:
    mods = osuMods.NOMOD
    LAZER_MODS = []

    for mod_str in mod_strings:
        try:
            mod_enum = osuMods.from_mod_string(mod_str)
            mods |= mod_enum
        except (KeyError, ValueError):
            LAZER_MODS.append(mod_str)
            print(f"Warning: Unknown mod '{mod_str}' in score. This mod will be ignored in the API v1-compatible legacy leaderboard, but should still work correctly in the lazer leaderboard if the client supports it.")

    return mods, LAZER_MODS

@dataclass
class LazerScore(Score):
    enabled_mods: list[str]

    @property
    def title(self) -> str:
        if self.enabled_mods:
            stable_mods, lazer_mods = seperate_lazer_and_stable_mods(self.enabled_mods)

            if lazer_mods:
                return f"[LAZER+{','.join(lazer_mods)}] {self.username}"

        return f"[LAZER] {self.username}"

@dataclass
class LegacyScore(Score):
    
    @property
    def title(self) -> str:
        return self.username

    def lazer_score(
        self,
        bonus_points: float = 0.0,
        mod_multiplier: float = 1.0,
        combo_weight: float = 0.7,
        accuracy_weight: float = 0.3
    ) -> int:

        total_hits = self.count300 + self.count100 + self.count50 + self.count_miss

        if total_hits == 0:
            return 0

        # Accuracy calculation (standard osu! weighting)
        accuracy = (self.count300 + self.count100 / 3 + self.count50 / 5) / total_hits

        # Hit score components (capped implicitly when max_combo/max_possible_combo ≤ 1 and accuracy ≤ 1)
        combo_portion = (self.max_combo / self.beatmap_max_combo) * combo_weight * 1_000_000
        accuracy_portion = accuracy * accuracy_weight * 1_000_000

        hit_score = combo_portion + accuracy_portion

        # The hit score should never exceed 1,000,000
        hit_score = min(hit_score, 1_000_000)

        # Add bonus (e.g., spinner spins, slider ticks) if known
        base_score = hit_score + bonus_points

        # Apply the 0.96× "Classic" multiplier (always present for imported scores)
        # Then apply any mod multiplier from the original play (DT, HT, etc.)
        final_score = base_score * 0.96 * mod_multiplier

        return round(final_score)

class ScoringAlgorithm(IntEnum):
    LAZER = 0
    PP = 1

class Scores(list[Score]):
    def __init__(
            self, 
            scores: list[Score] | None = None
        ):
        self.scoring_algorithm: ScoringAlgorithm = ScoringAlgorithm.LAZER
        super().__init__(scores or [])

    def copy(self) -> 'Scores':
        return Scores(scores=self[:])

    def remove_duplicates(self):
        new_scores = Scores()
        temp_scores: dict[str, list[Score]] = {}

        for score in self:
            if score.username not in temp_scores:
                temp_scores[score.username] = [score]
            else:
                temp_scores[score.username].append(score)
        
        for username, user_scores in temp_scores.items():
            if len(user_scores) == 1:
                new_scores += user_scores[0]
            else:
                # Keep whichever score ranks higher under the current sort metric.
                # This means lazer-only players keep their LazerScore, while stable
                # players whose LegacyScore outranks the v2 LazerScore representation
                # of the same play (e.g. HT mod) are also handled correctly.
                def _sort_key(s: Score) -> int:
                    if isinstance(s, LegacyScore):
                        return s.lazer_score()
                    return s.total_score

                new_scores += max(user_scores, key=_sort_key)

        self.clear()
        self.extend(new_scores)

    def set_scoring_algorithm(self, algorithm: ScoringAlgorithm):
        self.scoring_algorithm = algorithm

    def __iadd__(self, value: Score) -> 'Scores':
        super().append(value)
        return self

    def sort_by_algorithm(self):
        if self.scoring_algorithm == ScoringAlgorithm.PP:
            self.sort_by_pp()
        else:
            self.sort_by_score()

    def sort_by_pp(self):
        
        def pp_key(score: Score):
            return score.pp or 0

        self.sort(key=pp_key, reverse=True)

    def sort_by_score(self):

        def score_key(score: Score):
            if isinstance(score, LegacyScore):
                return score.lazer_score()
            
            return score.total_score
        
        self.sort(key=score_key, reverse=True)