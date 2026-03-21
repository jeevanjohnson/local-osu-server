from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import AliasChoices
from typing import Annotated
from osuProtocol.server_packets import osuMods
from pydantic import field_serializer, field_validator
from osuProtocol.server_packets import osuGameMode

if TYPE_CHECKING:
    from osuProtocol.client_web import ScoringAlgorithm

LAZER_MODS = list[str]

class Mods(list[str]):
    """A list of mods, represented as their short names. For example: ["HD", "HR", "DT"]"""

    def approximate_score_multiplier(self, rate: float) -> float:
        """
        Approximate the score multiplier for a given speed rate using linear interpolation.

        In osu!lazer, only three exact speed rates have official, ranked multipliers:
            - 0.75x → 0.30 (Half Time mod)
            - 1.00x → 1.00 (no speed mod)
            - 1.50x → 1.10 (Double Time / Nightcore mod)

        For any other rate, the game normally gives a score multiplier of 0.0 (unranked),
        but this function provides a smooth estimation by connecting the known points
        with straight lines – a method called linear interpolation.

        Linear interpolation assumes that the multiplier changes linearly between two
        known (rate, multiplier) pairs. For a desired rate that lies between two
        known rates, the multiplier is calculated as:
            multiplier = y1 + (rate - x1) * (y2 - y1) / (x2 - x1)
        where (x1, y1) and (x2, y2) are the neighboring known points.

        For rates outside the range 0.75–1.5, the function extrapolates (extends the
        line beyond the known points) using the nearest segment. This may produce
        unrealistic results (e.g., negative multipliers) if the rate is far outside,
        but is included for completeness.

        Parameters:
            rate (float): Desired speed multiplier (e.g., 1.0 for original speed).

        Returns:
            float: Estimated score multiplier based on linear interpolation.

        Examples:
            >>> approximate_score_multiplier(1.0)
            1.0
            >>> approximate_score_multiplier(1.5)
            1.1
            >>> approximate_score_multiplier(0.75)
            0.3
            >>> approximate_score_multiplier(1.125)   # Between 1.0 and 1.5
            1.05
            >>> approximate_score_multiplier(1.6)     # Extrapolated beyond 1.5
            1.1333...
        """
        # Known (rate, multiplier) points
        points = [
            (0.75, 0.30), 
            (1.00, 1.00), 
            (1.50, 1.10)
        ]
        # HT → 0.75x speed → 0.30x score
        # No speed change → 1.00x speed → 1.00x score
        # DT/NC → 1.50x speed → 1.10x score

        # Default to first segment so these are always defined.
        x1, y1 = points[0]
        x2, y2 = points[1]

        # Determine the segment to use (or extrapolate if outside)
        if rate < points[0][0]:
            # Extrapolate backward using the first segment
            x1, y1 = points[0]
            x2, y2 = points[1]
        elif rate > points[-1][0]:
            # Extrapolate forward using the last segment
            x1, y1 = points[-2]
            x2, y2 = points[-1]
        else:
            # Find the segment containing rate
            for i in range(len(points) - 1):
                if points[i][0] <= rate <= points[i + 1][0]:
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    break

        # Linear interpolation / extrapolation formula
        if x2 == x1:  # safety, should not happen
            return y1
        t = (rate - x1) / (x2 - x1)
        return y1 + t * (y2 - y1)
    
    def to_stable_mods(self) -> tuple[osuMods, LAZER_MODS]:
        stable_mods = osuMods.NOMOD
        lazer_mods = []

        for mod in self:
            try:
                stable_mods |= osuMods.from_acronym(mod)
            except ValueError:
                lazer_mods.append(mod)

        return stable_mods, lazer_mods
    
    def mod_multipler(
        self, 
        game_mode: osuGameMode
    ) -> float:
        if game_mode == osuGameMode.STANDARD:
            return self.mod_multiplier_standard()
        else:
            print(f"Warning: mod multiplier for game mode {game_mode} not implemented, returning 1.0")
            return 1.0
        
    def mod_multiplier_standard(self) -> float:
        multiplier = 1.0
        
        # Score multiplier mods in lazer
        mod_multipliers = {
            # Difficulty Reduction
            "EZ": 0.50,      # Easy
            "NF": 0.50,      # No Fail
            "HT": 0.30,      # Half Time
            "DC": 0.30,      # Daycore
            # "NR": 0.90,      # No Release (mania only, but multiplier applies)

            # Difficulty Increase
            "HR": 1.06,      # Hard Rock
            "SD": 1.00,      # Sudden Death
            "PF": 1.00,      # Perfect
            "DT": 1.10,      # Double Time
            "NC": 1.10,      # Nightcore (same as DT)
            "FI": 1.00,      # Fade In (mania)
            "HD": 1.06,      # Hidden
            "CO": 1.00,      # Cover (mania)
            "FL": 1.12,      # Flashlight
            "BL": 1.12,      # Blinds
            "ST": 1.00,      # Strict Tracking
            "AC": 1.00,      # Accuracy Challenge

            # Automation
            "AT": 1.00,      # Autoplay
            "CN": 1.00,      # Cinema
            # "RX": 0.10,      # Relax
            # "AP": 0.10,      # Autopilot
            "SO": 0.90,      # Spun Out

            # Conversion
            "TP": 0.10,      # Target Practice
            "DA": 0.50,      # Difficulty Adjust
            "CL": 0.96,      # Classic
            "RD": 1.00,      # Random
            "MR": 1.00,      # Mirror
            "AL": 1.00,      # Alternate
            "SW": 1.00,      # Swap
            "SG": 1.00,      # Single Tap
            "IN": 1.00,      # Invert (mania)
            "CS": 0.90,      # Constant Speed (mania)
            "HO": 0.90,      # Hold Off (mania)
            # xK mods (1K, 2K, etc.) have a 1.00x multiplier

            # Fun
            "TR": 1.00,      # Transform
            "WG": 1.00,      # Wiggle
            "SI": 1.00,      # Spin In
            "GR": 1.00,      # Grow
            "DF": 1.00,      # Deflate
            "WU": 0.50,      # Wind Up
            "WD": 0.50,      # Wind Down
            "TC": 1.00,      # Traceable
            "BR": 1.00,      # Barrel Roll
            "AD": 1.00,      # Approach Different
            "FF": 1.00,      # Floating Fruits (catch)
            "MU": 1.00,      # Muted
            "NS": 1.00,      # No Scope
            "MG": 0.50,      # Magnetised
            "RP": 1.00,      # Repel
            "AS": 0.50,      # Adaptive Speed
            "FR": 1.00,      # Freeze Frame
            "BU": 1.00,      # Bubbles
            "SY": 0.80,      # Synesthesia
            "DP": 1.00,      # Depth
        }

        # if DT is 1.10x and adjustes speed by 1.5x
        # & if HT is 0.30x and adjusts speed by 0.75x
        # & no speec changes is 1.00x
        
        for mod in self:
            if mod in mod_multipliers:
                if mod in ["DT", "NC", "HT", "DC"]:
                    # need to check if rate change so we can skip false multipler
                    rate_change = [m for m in self if m.endswith("x")]
                    if rate_change:
                        continue
                
                multiplier *= mod_multipliers[mod]
            elif mod.endswith("x"):
                rate = float(mod[:-1])
                multiplier *= self.approximate_score_multiplier(rate)
            else:
                print(f"Warning: unknown mod {mod} with no defined multiplier, ignoring in score calculation")
                continue
        
        return multiplier

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
    game_mode: osuGameMode
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
        final_score = base_score * 0.96 * self.enabled_mods.mod_multipler(self.game_mode)

        return round(final_score)

class StableScore(BaseScore):
    lazer: Literal[False] = False

class LazerScore(BaseScore):
    lazer: Literal[True] = True


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
            key=lambda s: (s.performance_points or 0, -s.time_set), 
            reverse=True
        )

    def sort_by_score(self):
        self.all_scores.sort(
            key=lambda s: (s.total_score, -s.time_set), 
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