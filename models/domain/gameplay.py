from typing import Any, Iterable, TypedDict

import ossapi.models

from osu_protocol.cho.server import osuGameMode, osuMods

# from adapters import log
from usecases.domain.calculator.linear_interpolation import linear_interpolation

LAZER_MODS = list[str]
_NON_SCORING_ATTRIBUTE_PREFIXES = ("AR", "OD", "HP", "CS")

ACRONYMS = list[str]

RATE = float
MULTIPLER = float

STABLE_RATES = (0.75, 1.0, 1.5)


def parse_difficulty_adjustment_settings(mod_settings: dict[str, Any]) -> list[str]:
    settings = []

    modifications = [
        ("cs_change", "CS"),
        ("approach_rate", "AR"),
        ("drain_rate", "HP"),
        ("overall_difficulty", "OD"),
    ]

    for setting_key, setting_prefix in modifications:
        setting_value = mod_settings.get(setting_key)
        if setting_value is not None:
            setting_value_length = len(str(setting_value))

            if setting_value_length > 4:
                setting_value = round(setting_value, 2)

            settings.append(f"{setting_prefix}{setting_value}")

    return settings


class AttributeModifiers(TypedDict):
    approach_rate: float | None
    overall_difficulty: float | None
    drain_rate: float | None
    cs_change: float | None


class Mods(ACRONYMS):
    """A list of mods, represented as short names, e.g. ['HD', 'HR', 'DT']."""

    def __init__(self, iterable: Iterable[str] | None = None) -> None:
        super().__init__(iterable or [])
        self.post_init()

    def difficulty_adjustments(self) -> AttributeModifiers:
        if "DA" not in self:
            return {
                "approach_rate": None,
                "overall_difficulty": None,
                "drain_rate": None,
                "cs_change": None,
            }

        modifiers: AttributeModifiers = {
            "approach_rate": None,
            "overall_difficulty": None,
            "drain_rate": None,
            "cs_change": None,
        }

        for mod in self:
            if mod.startswith(_NON_SCORING_ATTRIBUTE_PREFIXES):
                if mod.startswith("AR"):
                    modifiers["approach_rate"] = float(mod[2:])
                elif mod.startswith("OD"):
                    modifiers["overall_difficulty"] = float(mod[2:])
                elif mod.startswith("HP"):
                    modifiers["drain_rate"] = float(mod[2:])
                elif mod.startswith("CS"):
                    modifiers["cs_change"] = float(mod[2:])

        return modifiers

    @property
    def lazer_rate(self) -> bool:
        return self.rate() not in STABLE_RATES

    def rate(self) -> RATE:
        for mod in self:
            if mod.endswith("x"):
                try:
                    return float(mod[:-1])
                except ValueError:
                    print(f"Invalid rate change mod format: {mod}")
            return 1.5

        if "HT" in self or "DC" in self:
            return 0.75

        return 1.0

    def post_init(self):
        if "NC" in self and "DT" in self:
            print("Both NC and DT mods found, removing DT since NC includes DT")
            self.remove("DT")

    @property
    def stable(self) -> osuMods:
        stable_mods, _ = self.to_stable_mods()
        return stable_mods

    def __int__(self) -> int:
        stable_mods, _ = self.to_stable_mods()
        return int(stable_mods)

    def are_same(self, other: "Mods", ignore: ACRONYMS | None = None) -> bool:
        if ignore is None:
            ignore = []

        self_mods = [mod for mod in self if mod not in ignore]
        other_mods = [mod for mod in other if mod not in ignore]

        return self_mods == other_mods

    # Keep equality order-insensitive without mutating either operand.
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mods):
            return NotImplemented

        return sorted(self) == sorted(other)

    @classmethod
    def from_stable_mods(
        cls, stable_mods: osuMods | int, lazer_mods: LAZER_MODS | None = None
    ) -> "Mods":
        if isinstance(stable_mods, int):
            stable_mods = osuMods(stable_mods)

        mods = stable_mods.to_acronym_list()

        if lazer_mods:
            mods.extend(lazer_mods)

        return cls(mods)

    @classmethod
    def from_score_submission(cls, mods: int) -> "Mods":
        stable_mods = osuMods(mods)
        return cls.from_stable_mods(stable_mods, None)

    def approximate_score_multiplier_for(self, rate: RATE) -> MULTIPLER:
        points = [
            # (rate, multiplier)
            (0.75, 0.30),  # HT or DC multiples are 0.3x
            (1.00, 1.00),  # Base multiplier at 1.0x rate
            (1.50, 1.10),  # DT or NC multiples are 1.1x
        ]

        return linear_interpolation(
            input_value=rate,
            points=points,
        )

    def to_stable_mods(self) -> tuple[osuMods, LAZER_MODS]:
        stable_mods = osuMods.NOMOD
        lazer_mods = []

        for mod in self:
            try:
                stable_mods |= osuMods.from_acronym(mod)
            except ValueError:
                lazer_mods.append(mod)

        return stable_mods, lazer_mods

    def mod_multipler(self, game_mode: osuGameMode) -> float:
        if game_mode == osuGameMode.STANDARD:
            return self.mod_multiplier_standard()
        elif game_mode == osuGameMode.TAIKO:
            return self.mod_multiplier_taiko()
        elif game_mode == osuGameMode.CATCH_THE_BEAT:
            return self.mod_multiplier_catch()
        elif game_mode == osuGameMode.MANIA:
            return self.mod_multiplier_mania()

        print(
            f"Mod multiplier for game mode {game_mode} not implemented, defaulting to 1.0"
        )
        return 1.0

    def mod_multiplier_standard(self) -> float:
        """Calculate mod multiplier for osu!Standard."""
        multiplier = 1.0

        mod_multipliers = {
            "EZ": 0.50,
            "NF": 1.0,  # Override: No Fail always 1.0, doesn't affect multiplier
            "HT": 0.30,
            "DC": 0.30,
            "RX": 1.0,  # Override: Relax multiplier set to 1.0
            "AP": 1.0,  # Override: Autopilot multiplier set to 1.0
            "HD": 1.06,
            "HR": 1.06,
            "SD": 1.00,
            "PF": 1.00,
            "DT": 1.12,
            "NC": 1.12,
            "FI": 1.00,
            "CO": 1.00,
            "FL": 1.12,
            "BL": 1.12,
            "ST": 1.00,
            "AC": 1.00,
            "AT": 1.00,
            "CN": 1.00,
            "SO": 0.90,
            "TP": 0.10,
            "DA": 0.50,
            "CL": 0.96,
            "RD": 1.00,
            "MR": 1.00,
            "AL": 1.00,
            "SW": 1.00,
            "SG": 1.00,
            "IN": 1.00,
            "CS": 0.90,
            "HO": 0.90,
            "TR": 1.00,
            "WG": 1.00,
            "SI": 1.00,
            "GR": 1.00,
            "DF": 1.00,
            "WU": 0.50,
            "WD": 0.50,
            "TC": 1.00,
            "BR": 1.00,
            "AD": 1.00,
            "FF": 1.00,
            "MU": 1.00,
            "NS": 1.00,
            "TD": 1.00,
            "MG": 0.50,
            "RP": 1.00,
            "AS": 0.50,
            "FR": 1.00,
            "BU": 1.00,
            "SY": 0.80,
            "DP": 1.00,
            "SV2": 1.0,  # Override: Score V2 always 1.0, doesn't affect multiplier
        }

        rate_change = [m for m in self if m.endswith("x")]

        for mod in self:
            if mod in mod_multipliers:
                if mod in ["DT", "NC", "HT", "DC"] and rate_change:
                    continue
                else:
                    multiplier *= mod_multipliers[mod]
            elif mod.endswith("x"):
                rate = float(mod[:-1])
                multiplier *= self.approximate_score_multiplier_for(rate)
            elif mod.startswith(_NON_SCORING_ATTRIBUTE_PREFIXES):
                continue

        return multiplier

    def mod_multiplier_taiko(self) -> float:
        """Calculate mod multiplier for osu!Taiko."""
        multiplier = 1.0

        mod_multipliers = {
            "EZ": 0.50,
            "NF": 1.0,  # Override: No Fail always 1.0, doesn't affect multiplier
            "HT": 0.30,
            "DC": 0.30,
            "HD": 1.06,
            "HR": 1.06,
            "DT": 1.12,
            "NC": 1.12,
            "FL": 1.12,
            "RX": 1.0,  # Override: Relax multiplier set to 1.0
            "SD": 1.00,
            "PF": 1.00,
            "AT": 1.00,
            "CN": 1.00,
            "DA": 0.50,
            "CL": 0.96,
            "RD": 1.00,
            "SG": 1.00,
            "CS": 0.90,
            "TR": 1.00,
            "WG": 1.00,
            "SI": 1.00,
            "GR": 1.00,
            "DF": 1.00,
            "WU": 0.50,
            "WD": 0.50,
            "MU": 1.00,
            "MG": 0.50,
            "AS": 0.50,
            "SY": 0.80,
            "DP": 1.00,
            "SV2": 1.0,  # Override: Score V2 always 1.0, doesn't affect multiplier
        }

        rate_change = [m for m in self if m.endswith("x")]

        for mod in self:
            if mod in mod_multipliers:
                if mod in ["DT", "NC", "HT", "DC"] and rate_change:
                    continue
                else:
                    multiplier *= mod_multipliers[mod]
            elif mod.endswith("x"):
                rate = float(mod[:-1])
                multiplier *= self.approximate_score_multiplier_for(rate)
            elif mod.startswith(_NON_SCORING_ATTRIBUTE_PREFIXES):
                continue

        return multiplier

    def mod_multiplier_catch(self) -> float:
        """Calculate mod multiplier for osu!Catch."""
        multiplier = 1.0

        mod_multipliers = {
            "EZ": 0.50,
            "NF": 1.0,  # Override: No Fail always 1.0, doesn't affect multiplier
            "HT": 0.30,
            "DC": 0.30,
            "HD": 1.06,
            "HR": 1.06,
            "DT": 1.06,
            "NC": 1.06,
            "FL": 1.12,
            "RX": 1.0,  # Override: Relax multiplier set to 1.0
            "SD": 1.00,
            "PF": 1.00,
            "AT": 1.00,
            "CN": 1.00,
            "DA": 0.50,
            "CL": 0.96,
            "RD": 1.00,
            "MR": 1.00,
            "TR": 1.00,
            "WG": 1.00,
            "SI": 1.00,
            "GR": 1.00,
            "DF": 1.00,
            "WU": 0.50,
            "WD": 0.50,
            "NS": 1.00,
            "FF": 1.00,
            "MU": 1.00,
            "SY": 0.80,
            "DP": 1.00,
            "SV2": 1.0,  # Override: Score V2 always 1.0, doesn't affect multiplier
        }

        rate_change = [m for m in self if m.endswith("x")]

        for mod in self:
            if mod in mod_multipliers:
                if mod in ["DT", "NC", "HT", "DC"] and rate_change:
                    continue
                else:
                    multiplier *= mod_multipliers[mod]
            elif mod.endswith("x"):
                rate = float(mod[:-1])
                multiplier *= self.approximate_score_multiplier_for(rate)
            elif mod.startswith(_NON_SCORING_ATTRIBUTE_PREFIXES):
                continue

        return multiplier

    def mod_multiplier_mania(self) -> float:
        """Calculate mod multiplier for osu!Mania."""
        multiplier = 1.0

        mod_multipliers = {
            "EZ": 0.50,
            "NF": 1.0,  # Override: No Fail always 1.0, doesn't affect multiplier
            "HT": 0.50,
            "DC": 0.50,
            "HD": 1.06,
            "HR": 1.06,
            "DT": 1.0,  # Rate increase mods get 1x in Mania
            "NC": 1.0,
            "FL": 1.12,
            "SD": 1.00,
            "PF": 1.00,
            "AT": 1.00,
            "CN": 1.00,
            "DA": 0.50,
            "CL": 0.96,
            "RD": 1.00,
            "CO": 1.00,
            "FI": 1.00,
            "IN": 1.00,
            "HO": 1.00,
            "TR": 1.00,
            "WG": 1.00,
            "SI": 1.00,
            "GR": 1.00,
            "DF": 1.00,
            "WU": 0.50,
            "WD": 0.50,
            "TC": 1.00,
            "BR": 1.00,
            "MU": 1.00,
            "SY": 0.80,
            "DP": 1.00,
            "SV2": 1.0,  # Override: Score V2 always 1.0, doesn't affect multiplier
        }

        rate_change = [m for m in self if m.endswith("x")]

        for mod in self:
            if mod in mod_multipliers:
                if mod in ["DT", "NC", "HT", "DC"] and rate_change:
                    continue
                else:
                    multiplier *= mod_multipliers[mod]
            elif mod.endswith("x"):
                rate = float(mod[:-1])
                multiplier *= self.approximate_score_multiplier_for(rate)
            elif mod.startswith(_NON_SCORING_ATTRIBUTE_PREFIXES):
                continue
            elif mod in ["1K", "2K", "3K", "4K", "5K", "6K", "7K", "8K", "9K", "10K"]:
                multiplier *= 0.9

        return multiplier

    @classmethod
    def from_api_v2(cls, mods: list[ossapi.models.NonLegacyMod]) -> "Mods":
        score_mods = []
        for mod in mods:
            mod_settings: dict[str, Any] = mod.settings

            if mod_settings:
                score_mods.append(mod.acronym)

                if mod_settings.get("speed_change"):
                    speed_change = mod_settings["speed_change"]
                    if speed_change != 1.5 and speed_change != 0.75:
                        score_mods.append(f"{speed_change}x")

                if mod.acronym == "DA":
                    score_mods.extend(
                        parse_difficulty_adjustment_settings(mod_settings)
                    )
                    # log.warning(
                    #     f"Error processing mod settings for mod {mod.acronym}: {e}\nMod settings: {mod.settings}"
                    # )
            else:
                score_mods.append(mod.acronym)

        return cls(score_mods)

    def __repr__(self) -> str:
        return ",".join(self)

    def __str__(self) -> str:
        rep = self.__repr__()

        if rep == "":
            return "NM"

        return rep

    @classmethod
    def from_stable_string(cls, stable_mods_str: str) -> "Mods":
        # for every 2 chars in the string
        stable_mods = osuMods.NOMOD
        for i in range(0, len(stable_mods_str), 2):
            mod_acronym = stable_mods_str[i : i + 2]
            stable_mods |= osuMods.from_acronym(mod_acronym)

        return cls.from_stable_mods(stable_mods)

    @classmethod
    def from_stable_int(cls, stable_mods_int: int) -> "Mods":
        stable_mods = osuMods(stable_mods_int)
        return cls.from_stable_mods(stable_mods)

    def to_stable_mods_int(self) -> int:
        stable_mods, _ = self.to_stable_mods()
        return int(stable_mods)
