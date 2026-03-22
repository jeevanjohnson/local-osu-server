from adapters.app_logger import app_logger
from osuProtocol.server_packets import osuGameMode, osuMods

LAZER_MODS = list[str]
_NON_SCORING_ATTRIBUTE_PREFIXES = ("AR", "OD", "HP", "CS")


class Mods(list[str]):
    """A list of mods, represented as short names, e.g. ['HD', 'HR', 'DT']."""

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

    def approximate_score_multiplier(self, rate: float) -> float:
        # Known (rate, multiplier) points.
        points = [(0.75, 0.30), (1.00, 1.00), (1.50, 1.10)]

        x1, y1 = points[0]
        x2, y2 = points[1]

        if rate < points[0][0]:
            x1, y1 = points[0]
            x2, y2 = points[1]
        elif rate > points[-1][0]:
            x1, y1 = points[-2]
            x2, y2 = points[-1]
        else:
            for i in range(len(points) - 1):
                if points[i][0] <= rate <= points[i + 1][0]:
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    break

        if x2 == x1:
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

    def mod_multipler(self, game_mode: osuGameMode) -> float:
        if game_mode == osuGameMode.STANDARD:
            return self.mod_multiplier_standard()

        app_logger.warning(
            f"Mod multiplier for game mode {game_mode} not implemented, defaulting to 1.0"
        )
        return 1.0

    def mod_multiplier_standard(self) -> float:
        multiplier = 1.0

        mod_multipliers = {
            "EZ": 0.50,
            "NF": 0.50,
            "HT": 0.30,
            "DC": 0.30,
            "RX": 1.00,
            "AP": 1.00,
            "HR": 1.06,
            "SD": 1.00,
            "PF": 1.00,
            "DT": 1.10,
            "NC": 1.10,
            "FI": 1.00,
            "HD": 1.06,
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
        }

        rate_change = [m for m in self if m.endswith("x")]

        for mod in self:
            if mod in mod_multipliers:
                if mod in ["DT", "NC", "HT", "DC"] and rate_change:
                    # Ignore DT/NC/HT/DC if there's a rate change mod, since the rate change mod will handle the multiplier for those mods
                    continue
                else:
                    multiplier *= mod_multipliers[mod]
            elif mod.endswith("x"):
                rate = float(mod[:-1])
                multiplier *= self.approximate_score_multiplier(rate)
            elif mod.startswith(_NON_SCORING_ATTRIBUTE_PREFIXES):
                # DA settings like AR10.5/OD8/HP6/CS4 affect map attributes, not score multiplier.
                continue
            else:
                app_logger.warning(
                    f"Unknown mod {mod} with no defined multiplier, ignoring in score calculation"
                )

        return multiplier
