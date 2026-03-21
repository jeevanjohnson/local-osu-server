from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import AliasChoices
from typing import Annotated
from osuProtocol.server_packets import osuMods
from pydantic import field_serializer, field_validator

if TYPE_CHECKING:
    from osuProtocol.client_web import ScoringAlgorithm

LAZER_MODS = list[str]

class Mods(list[str]):
    """A list of mods, represented as their short names. For example: ["HD", "HR", "DT"]"""
    
    def to_stable_mods(self) -> tuple[osuMods, LAZER_MODS]:
        stable_mods = osuMods.NOMOD
        lazer_mods = []

        for mod in self:
            try:
                stable_mods |= osuMods.from_acronym(mod)
            except ValueError:
                lazer_mods.append(mod)

        return stable_mods, lazer_mods
    
EpochTime = int

class Combo(BaseModel):
    actual: int
    max: int

class BaseScore(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    score_id: int
    username: str
    total_score_value: int = Field(
        validation_alias=AliasChoices("_total_score", "total_score"),
        serialization_alias="_total_score",
    )
    combo: Combo
    count50: int
    count100: int
    count300: int
    count_miss: int
    perfect: bool
    enabled_mods: Mods
    user_id: int
    time_set: EpochTime
    replay_available: bool

    lazer: bool = Field(default=False)
    performance_points: int | None = Field(default=None)

    @field_serializer("enabled_mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)
    
    @field_validator("enabled_mods", mode="before")
    @classmethod
    def deserialize_mods(cls, value: list[str]) -> Mods:
        return Mods(value)

    # Self calc scores regardless of whether it's lazer or stable
    # this allows more accurate score sorting for leaderboards
    @property
    def total_score(self) -> int:
        # Note: bonus_points only comes from spinner over-spin (not implemented here)
        bonus_points: float = 0.0

        total_hits = self.count300 + self.count100 + self.count50 + self.count_miss

        if total_hits == 0:
            return 0

        # Accuracy calculation (standard osu! weighting)
        accuracy = (self.count300 + self.count100 / 3 + self.count50 / 5) / total_hits

        # Combo progress: achieved combo / max possible combo
        combo_progress = self.combo.actual / self.combo.max if self.combo.max > 0 else 0

        # Accuracy progress: in osu!standard this is always 1.0
        accuracy_progress = 1.0

        # Correct lazer scoring formula (two 500k terms)
        hit_score = (
            500_000 * accuracy * combo_progress +
            500_000 * (accuracy ** 5) * accuracy_progress
        )

        # Add bonus points (spinner overspins)
        base_score = hit_score + bonus_points

        # Apply the 0.96× "Classic" multiplier (always present for imported scores)
        # Then apply any mod multiplier from the original play (DT, HT, etc.)
        final_score = base_score * 0.96 * self.mod_multiplier

        return round(final_score)

    @property
    def mod_multiplier(self) -> float:
        raise NotImplementedError("mod_multiplier should be implemented in subclasses")

class StableScore(BaseScore):
    lazer: Literal[False] = False

    @property
    def mod_multiplier(self) -> float:
        """
        Calculate score multiplier based on enabled mods
        This is a simplified version - you'll need to adjust based on exact lazer behavior
        """
        multiplier = 1.0
        
        # Score multiplier mods in lazer
        mod_multipliers = {
            "EZ": 0.5,      # Easy
            "NF": 1.0,      # No Fail (no multiplier)
            "HT": 0.9,      # Half Time
            "HR": 1.06,     # Hard Rock
            "DT": 1.12,     # Double Time
            "NC": 1.12,     # Nightcore (same as DT)
            "HD": 1.06,    # Hidden (TODO: Verify this multiplier)
            "FL": 1.0,      # Flashlight (adds bonus points instead)
            "SO": 1.0,      # Spun Out
            "SD": 1.0,      # Sudden Death
            "PF": 1.0,      # Perfect
            "RX": 0.0,      # Relax (no score)
            "AP": 0.0,      # Auto Pilot (no score)
        }
        
        for mod in self.enabled_mods:
            if mod in mod_multipliers:
                multiplier *= mod_multipliers[mod]
        
        return multiplier

class LazerScore(BaseScore):
    lazer: Literal[True] = True

    @property
    def mod_multiplier(self) -> float:
        """
        Calculate score multiplier based on enabled mods
        This is a simplified version - you'll need to adjust based on exact lazer behavior
        """
        multiplier = 1.0
        
        # Score multiplier mods in lazer
        # https://osu.ppy.sh/community/forums/topics/1959149?n=2https://osu.ppy.sh/community/forums/topics/1959149?n=2
        mod_multipliers = {
            "EZ": 0.5,      # Easy
            "NF": 1.0,      # No Fail (no multiplier)
            "HT": 0.9,      # Half Time
            "HR": 1.06,     # Hard Rock
            "DT": 1.12,     # Double Time
            "NC": 1.12,     # Nightcore (same as DT)
            # "HD": 1.06,    # Hidden (TODO: Verify this multiplier)
            "FL": 1.0,      # Flashlight (adds bonus points instead)
            "SO": 1.0,      # Spun Out
            "SD": 1.0,      # Sudden Death
            "PF": 1.0,      # Perfect
            "RX": 0.0,      # Relax (no score)
            "AP": 0.0,      # Auto Pilot (no score)
            "WU": 0.5,     # Wind Up
            "WD": 0.5,     # Wind Down
            "DA": 0.5     # Difficulty Adjust
        }
        
        for mod in self.enabled_mods:
            if mod in mod_multipliers:
                multiplier *= mod_multipliers[mod]
        
        return multiplier

Score = Annotated[StableScore | LazerScore, Field(discriminator="lazer")]

class Scores(BaseModel):
    limit: int = Field(default=50)
    all_scores: list[Score]

    @property
    def scores(self) -> list[Score]:
        return self.all_scores[:self.limit]

    @property
    def total(self) -> int:
        return len(self.scores)

    def sort_by_pp(self) -> None:
        self.all_scores.sort(
            key=lambda s: s.performance_points or 0, 
            reverse=True
        )

    def sort_by_score(self):
        self.all_scores.sort(
            key=lambda s: s.total_score, 
            reverse=True
        )
    
    def sort(self, algorithm: "ScoringAlgorithm") -> None:
        # Lazy import prevents circular import at module load time.
        from osuProtocol.client_web import ScoringAlgorithm

        if algorithm == ScoringAlgorithm.PP:
            self.sort_by_pp()
        elif algorithm == ScoringAlgorithm.LAZER:
            self.sort_by_score()
        else:
            raise ValueError(f"Unsupported scoring algorithm: {algorithm}")