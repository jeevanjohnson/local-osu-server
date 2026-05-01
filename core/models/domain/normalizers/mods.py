
from typing import Any, Iterable, TypedDict

import ossapi.models

from server.adapters.osu_protocol.enums import ClientMods
from core.models.domain.normalizers.game_mode import GameMode
from jays_tools.architecture import DomainModel
from core.usecases.adapters.statistics import LinearInterpolation


class AttributeAdjustmentResult(TypedDict):
    hp: float | None
    cs: float | None
    od: float | None
    ar: float | None


class SplitModsResult(TypedDict):
    stable_mods: ClientMods
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


class Mods(list[str], DomainModel):
    """A list of mods, represented as short names, e.g. ['HD', 'HR', 'DT']."""

    def __init__(self, iterable: Iterable[str] | None = None) -> None:
        super().__init__(iterable or [])

    def __int__(self) -> int:
        stable_mods = self.to_stable_mods()
        return int(stable_mods)

    def __ne__(self, other: "Mods") -> bool:
        return not self.__eq__(other)

    def __eq__(self, other: "Mods") -> bool:
        return sorted(self) == sorted(other)

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
    def from_stable_mods(cls, stable_mods: ClientMods) -> "Mods":
        mods_list = []
        for mod in ClientMods:
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
                final_mods.append("DA")
                continue

            if mod.acronym in ("WU", "WD"):
                initial_rate = mod_settings["initial_rate"]
                final_rate = mod_settings["final_rate"]
                final_mods.append(
                    f"{mod.acronym}({initial_rate}->{final_rate})")
                continue

            print(f"UNHANDLED Mods: {mod.acronym}, settings: {mod_settings}")
            final_mods.append(mod.acronym)

        return cls.from_list(final_mods)

    @classmethod
    def from_stable_int(cls, stable_mods_int: int) -> "Mods":
        stable_mods = ClientMods(stable_mods_int)
        return cls.from_stable_mods(stable_mods)

    @staticmethod
    def normalize_stable_mod(stable_mod: ClientMods) -> str:
        return {
            ClientMods.DOUBLETIME: "DT",
            ClientMods.NIGHTCORE: "NC",
            ClientMods.HARDROCK: "HR",
            ClientMods.HIDDEN: "HD",
            ClientMods.FLASHLIGHT: "FL",
            ClientMods.EASY: "EZ",
            ClientMods.NOFAIL: "NF",
            ClientMods.SUDDENDEATH: "SD",
            ClientMods.TOUCHSCREEN: "TD",
            ClientMods.RELAX: "RX",
            ClientMods.HALFTIME: "HT",
            ClientMods.AUTOPLAY: "AU",
            ClientMods.SPUNOUT: "SO",
            ClientMods.AUTOPILOT: "AP",
            ClientMods.PERFECT: "PF",
            ClientMods.KEY4: "4K",
            ClientMods.KEY5: "5K",
            ClientMods.KEY6: "6K",
            ClientMods.KEY7: "7K",
            ClientMods.KEY8: "8K",
            ClientMods.FADEIN: "FI",
            ClientMods.RANDOM: "RN",
            ClientMods.CINEMA: "CM",
            ClientMods.TARGET: "TP",
            ClientMods.KEY9: "9K",
            ClientMods.KEYCOOP: "COOP",
            ClientMods.KEY1: "1K",
            ClientMods.KEY3: "3K",
            ClientMods.KEY2: "2K",
            ClientMods.SCOREV2: "SV2",
            ClientMods.MIRROR: "MR",
        }[stable_mod]

    @staticmethod
    def stable_mod_from_acronym(acronym: str) -> ClientMods:
        return {
            "DT": ClientMods.DOUBLETIME,
            "NC": ClientMods.NIGHTCORE,
            "HR": ClientMods.HARDROCK,
            "HD": ClientMods.HIDDEN,
            "FL": ClientMods.FLASHLIGHT,
            "EZ": ClientMods.EASY,
            "NF": ClientMods.NOFAIL,
            "SD": ClientMods.SUDDENDEATH,
            "TD": ClientMods.TOUCHSCREEN,
            "RX": ClientMods.RELAX,
            "HT": ClientMods.HALFTIME,
            "AU": ClientMods.AUTOPLAY,
            "SO": ClientMods.SPUNOUT,
            "AP": ClientMods.AUTOPILOT,
            "PF": ClientMods.PERFECT,
            "4K": ClientMods.KEY4,
            "5K": ClientMods.KEY5,
            "6K": ClientMods.KEY6,
            "7K": ClientMods.KEY7,
            "8K": ClientMods.KEY8,
            "FI": ClientMods.FADEIN,
            "RN": ClientMods.RANDOM,
            "CM": ClientMods.CINEMA,
            "TP": ClientMods.TARGET,
            "9K": ClientMods.KEY9,
            "COOP": ClientMods.KEYCOOP,
            "1K": ClientMods.KEY1,
            "3K": ClientMods.KEY3,
            "2K": ClientMods.KEY2,
            "SV2": ClientMods.SCOREV2,
            "MR": ClientMods.MIRROR,
        }[acronym]

    def rate(self) -> RateResult:
        rate = None

        for mod in self:
            if mod.endswith("X"):
                rate = float(mod.removesuffix("X"))
                break

        if rate is None:
            for mod in self:
                if mod.startswith(("WU", "WD")):
                    try:
                        rate_part = mod[2:].strip("()")
                        initial_rate_str, final_rate_str = rate_part.split(
                            "->")
                        initial_rate = float(initial_rate_str)
                        final_rate = float(final_rate_str)
                        rate = (initial_rate + final_rate) / 2
                    except Exception:
                        pass

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

        score_mult = score_multiplier.approximate(rate)

        return RateResult(
            rate=rate,
            score_multiplier=score_mult
        )

    def custom_rate(self) -> bool:
        return any(mod.endswith("X") or mod.startswith(("WU", "WD")) for mod in self)

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

    def attribute_adjustments(self) -> AttributeAdjustmentResult:
        hp = None
        cs = None
        od = None
        ar = None

        for mod in self:
            if mod.startswith("HP"):
                try:
                    hp = float(mod.removeprefix("HP"))
                except ValueError:
                    pass
            elif mod.startswith("CS"):
                try:
                    cs = float(mod.removeprefix("CS"))
                except ValueError:
                    pass
            elif mod.startswith("OD"):
                try:
                    od = float(mod.removeprefix("OD"))
                except ValueError:
                    pass
            elif mod.startswith("AR"):
                try:
                    ar = float(mod.removeprefix("AR"))
                except ValueError:
                    pass

        return AttributeAdjustmentResult(
            hp=hp,
            cs=cs,
            od=od,
            ar=ar
        )

    def split_mods(self) -> SplitModsResult:
        stable_mods = ClientMods.NOMOD
        lazer_mods = []

        for mod in self:
            try:
                stable_mods |= self.stable_mod_from_acronym(mod)
            except ValueError:
                lazer_mods.append(mod)

        if stable_mods & ClientMods.NIGHTCORE:
            stable_mods |= ClientMods.DOUBLETIME

        if stable_mods & ClientMods.PERFECT:
            stable_mods |= ClientMods.SUDDENDEATH

        return SplitModsResult(
            stable_mods=stable_mods,
            lazer_mods=lazer_mods
        )

    def to_str(self, include_rate: bool = False, remove: list[str] | None = None) -> str:
        if not self:
            if remove and "NM" in remove:
                return ""
            return "NM"

        copy = self.copy()

        if include_rate:
            if not any(mod.endswith("X") for mod in copy):
                if "HT" in copy or "DC" in copy:
                    copy.append(".75X")
                elif "DT" in copy or "NC" in copy:
                    copy.append("1.5X")
                else:
                    copy.append("1.0X")

            if "HT" in copy:
                copy.remove("HT")
            if "DC" in copy:
                copy.remove("DC")
            if "DT" in copy:
                copy.remove("DT")
            if "NC" in copy:
                copy.remove("NC")

        if remove:
            for mod in remove:
                if mod in copy:
                    copy.remove(mod)

        return ",".join(copy)

    def _to_osu_api_v2(self) -> list[str]:
        result = []

        for mod in self:
            if mod.endswith("X"):
                continue

            if mod.startswith(("AR", "OD", "HP", "CS")):
                continue

            result.append(f"mods[]={mod}")

        return result

    def to_osu_api_v2(self) -> int:
        stable_mods = self.to_stable_mods()

        stable_mods &= ~ClientMods.SCOREV2
        stable_mods &= ~ClientMods.RELAX
        stable_mods &= ~ClientMods.AUTOPILOT

        return int(stable_mods)

    def to_stable_mods(self, remove_rate_mods: bool = False) -> ClientMods:
        result = self.split_mods()
        stable_mods = result["stable_mods"]

        if remove_rate_mods:
            stable_mods &= ~ClientMods.DOUBLETIME
            stable_mods &= ~ClientMods.NIGHTCORE
            stable_mods &= ~ClientMods.HALFTIME

        return stable_mods

    def to_lazer_specific_mods(self, ignore: list[str] | None = None, include_rate: bool = False) -> list[str]:
        result = self.split_mods()
        lazer_mods = result["lazer_mods"]

        if ignore:
            lazer_mods = [mod for mod in lazer_mods if mod not in ignore]

        if include_rate:
            rate_result = self.rate()
            rate_mod = f"{rate_result['rate']}X"
            if rate_mod not in lazer_mods:
                lazer_mods.append(rate_mod)

        return lazer_mods

    def multiplier(self, mode: GameMode) -> float:
        if mode == GameMode.STANDARD:
            return self.multiplier_standard()
        elif mode == GameMode.TAIKO:
            return self.multiplier_taiko()
        elif mode == GameMode.CATCH:
            return self.multiplier_catch()
        elif mode == GameMode.MANIA:
            return self.multiplier_mania()

        print(
            f"Mod multiplier for game mode {mode} not implemented, defaulting to 1.0"
        )
        return 1.0

    def multiplier_standard(self) -> float:
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
            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]

        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

        return multiplier

    def multiplier_taiko(self) -> float:
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
            "MU": 1.00,
            "MG": 0.50,
            "AS": 0.50,
            "SY": 0.80,
            "DP": 1.00,
            "SV2": 1.0,  # Override: Score V2 always 1.0, doesn't affect multiplier
            "DA": 0.50,
        }

        for mod in self:
            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]

        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

        return multiplier

    def multiplier_catch(self) -> float:
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
            "NS": 1.00,
            "FF": 1.00,
            "MU": 1.00,
            "SY": 0.80,
            "DP": 1.00,
            "SV2": 1.0,  # Override: Score V2 always 1.0, doesn't affect multiplier
        }

        for mod in self:
            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]

        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

        return multiplier

    def multiplier_mania(self) -> float:
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
            if mod not in mod_multipliers:
                continue

            multiplier *= mod_multipliers[mod]

        if self.custom_rate():
            rate_result = self.rate()
            multiplier *= rate_result["score_multiplier"]

        return multiplier
