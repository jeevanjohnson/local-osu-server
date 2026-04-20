from enum import IntEnum
from typing import Any, Iterable, TypedDict

import ossapi.models

from core.osu_protocol.cho.server import osuMods
from core.usecases.adapters.statistics import LinearInterpolation

class GameMode(IntEnum):
    STANDARD = 0
    TAIKO = 1
    CATCH = 2
    MANIA = 3

class SplitModsResult(TypedDict):
    stable_mods: osuMods
    lazer_mods: list[str]

class RateResult(TypedDict):
    rate: float
    score_multiplier: float

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

class Mods(list[str]):
    """A list of mods, represented as short names, e.g. ['HD', 'HR', 'DT']."""

    def __init__(self, iterable: Iterable[str]) -> None:
        super().__init__(iterable)

    def __int__(self) -> int:
        stable_mods = self.to_stable_mods()
        return int(stable_mods)

    def __eq__(self, other: "Mods") -> bool:
        return sorted(self) == sorted(other)

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return ",".join(self)

    @classmethod
    def from_list(cls, mods_list: list[str]) -> "Mods":
        mods_list = [mod.strip().upper() for mod in mods_list if mod.strip()]

        if "NC" in mods_list and "DT" in mods_list:
            mods_list.remove("DT")

        custom_rate_mods = [mod for mod in mods_list if mod.endswith("X")]
        if custom_rate_mods:
            for constant_rate_mod in ["DT", "NC", "HT", "DC"]:
                if constant_rate_mod in mods_list:
                    mods_list.remove(constant_rate_mod)
        
        if "DA" in mods_list:
            mods_list.remove("DA")

        return cls(mods_list)

    @classmethod
    def from_stable_mods(cls, stable_mods: osuMods) -> "Mods":
        mods_list = []
        for mod in osuMods:
            if stable_mods & mod:
                mods_list.append(
                    cls.normalize_stable_mod(mod)
                )

        return cls.from_list(mods_list)

    @classmethod
    def from_api_v2(cls, mods: list[ossapi.models.NonLegacyMod]) -> "Mods":
        final_mods = []

        for mod in mods:
            if not mod.settings:
                final_mods.append(mod.acronym)
                continue
                
            mod_settings: dict[str, Any] = mod.settings

            rate = mod_settings.get("speed_change")
            if rate is not None:
                if rate not in (1.5, 0.75, 1.0):
                    final_mods.append(f"{rate}x")
                else:
                    final_mods.append(mod.acronym)
            
                continue

            if mod.acronym == "DA":
                final_mods.extend(
                    parse_difficulty_adjustment_settings(mod_settings)
                )
        
        return cls.from_list(final_mods)
    
    @classmethod
    def from_stable_int(cls, stable_mods_int: int) -> "Mods":
        stable_mods = osuMods(stable_mods_int)
        return cls.from_stable_mods(stable_mods)

    @staticmethod
    def normalize_stable_mod(stable_mod: osuMods) -> str:
        return {
            osuMods.DOUBLETIME: "DT",
            osuMods.NIGHTCORE: "NC",
            osuMods.HARDROCK: "HR",
            osuMods.HIDDEN: "HD",
            osuMods.FLASHLIGHT: "FL",
            osuMods.EASY: "EZ",
            osuMods.NOFAIL: "NF",
            osuMods.SUDDENDEATH: "SD",
            osuMods.TOUCHSCREEN: "TD",
            osuMods.RELAX: "RX",
            osuMods.HALFTIME: "HT",
            osuMods.AUTOPLAY: "AU",
            osuMods.SPUNOUT: "SO",
            osuMods.AUTOPILOT: "AP",
            osuMods.PERFECT: "PF",
            osuMods.KEY4: "4K",
            osuMods.KEY5: "5K",
            osuMods.KEY6: "6K",
            osuMods.KEY7: "7K",
            osuMods.KEY8: "8K",
            osuMods.FADEIN: "FI",
            osuMods.RANDOM: "RN",
            osuMods.CINEMA: "CM",
            osuMods.TARGET: "TP",
            osuMods.KEY9: "9K",
            osuMods.KEYCOOP: "COOP",
            osuMods.KEY1: "1K",
            osuMods.KEY3: "3K",
            osuMods.KEY2: "2K",
            osuMods.SCOREV2: "SV2",
            osuMods.MIRROR: "MR",
        }[stable_mod]

    def rate(self) -> RateResult:
        rate = None 

        for mod in self:
            if mod.endswith("X"):
                rate = float(mod.removesuffix("X"))

        if rate is None:
            if "HT" in self or "DC" in self:
                rate = 0.75
            elif "DT" in self or "NC" in self:
                rate = 1.5
            else:
                rate = 1.0
        
        score_multiplier = LinearInterpolation(
            known_points=[
                (0.75, 0.30),  # HT or DC multiples are 0.3x
                (1.00, 1.00),  # Base multiplier at 1.0x rate
                (1.50, 1.10),  # DT or NC multiples are 1.1x
            ]
        )

        return RateResult(
            rate=rate,
            score_multiplier=score_multiplier.approximate(rate)
        )

    def custom_rate(self) -> bool:
        return any(mod.endswith("X") for mod in self)

    def same_as(self, other: "Mods", ignore: "Mods | None" = None) -> bool:
        self_mods = list(self)
        other_mods = list(other)

        if ignore is not None:
            for mod in ignore:
                if mod in self_mods:
                    self_mods.remove(mod)
                if mod in other_mods:
                    other_mods.remove(mod)

        return self_mods == other_mods

    def split_mods(self) -> SplitModsResult:
        stable_mods = osuMods.NOMOD
        lazer_mods = []

        for mod in self:
            try:
                stable_mods |= osuMods.from_acronym(mod)
            except ValueError:
                lazer_mods.append(mod)

        return SplitModsResult(
            stable_mods=stable_mods, 
            lazer_mods=lazer_mods
        )

    def to_osu_api_v2(self) -> list[str]:
        result = []

        for mod in self:
            if mod.startswith("X"):
                continue

            if mod.startswith(("AR", "OD", "HP", "CS")):
                continue

            result.append(f"mods[]={mod}")

        return result

    def to_stable_mods(self) -> osuMods:
        result = self.split_mods()
        return result["stable_mods"]

    def to_lazer_specific_mods(self) -> list[str]:
        result = self.split_mods()
        return result["lazer_mods"]

    def mod_multipler(self, mode: GameMode) -> float:
        if mode == GameMode.STANDARD:
            return self.mod_multiplier_standard()
        elif mode == GameMode.TAIKO:
            return self.mod_multiplier_taiko()
        elif mode == GameMode.CATCH:
            return self.mod_multiplier_catch()
        elif mode == GameMode.MANIA:
            return self.mod_multiplier_mania()

        print(
            f"Mod multiplier for game mode {mode} not implemented, defaulting to 1.0"
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

        for mod in self:
            if mod.startswith(("AR", "OD", "HP", "CS")):
                # TODO: compensate for these changes
                continue

            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]
        
        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

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

        for mod in self:
            if mod.startswith(("AR", "OD", "HP", "CS")):
                # TODO: compensate for these changes
                continue

            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]
        
        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

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

        for mod in self:
            if mod.startswith(("AR", "OD", "HP", "CS")):
                # TODO: compensate for these changes
                continue

            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]
        
        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

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
            "1K": 0.90,
            "2K": 0.90,
            "3K": 0.90,
            "4K": 0.90,
            "5K": 0.90,
            "6K": 0.90,
            "7K": 0.90,
            "8K": 0.90,
            "9K": 0.90,
            "10K": 0.90,
        }

        for mod in self:
            if mod.startswith(("AR", "OD", "HP", "CS")):
                # TODO: compensate for these changes
                continue

            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]
        
        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

        return multiplier
