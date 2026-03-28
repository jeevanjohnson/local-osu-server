from typing import Literal

from models.domain.gameplay import osuGameMode

from usecases.domain.calculator.linear_interpolation import (
    linear_interpolation as usecases_domain_calculator_interpolation,
    power_law_interpolation as usecases_domain_calculator_power_law,
)
import usecases.domain.cache_control
from constants.paths import SNAPSHOTS
import json

PP = int
RANK = int

@usecases.domain.cache_control.cache_group("performance")
def local(
    input: PP | RANK, output_type: Literal["pp", "rank"], game_mode: osuGameMode
) -> RANK | PP:
    latest_snapshot = max(SNAPSHOTS.iterdir())

    snap_shot_data = json.loads(latest_snapshot.read_text())

    data_points = snap_shot_data[game_mode.to_snapshot()]

    # Use power-law model for rank calculation (PP -> rank) since that distribution is exponential
    # Use linear interpolation for reverse (rank -> PP) which is less sensitive
    if output_type == "rank":
        result = usecases_domain_calculator_power_law(
            input_value=input,
            points=data_points,
            input_key=lambda p: p[1],  # PP is input
            output_key=lambda p: p[0],  # Rank is output
            clamp=False,  # Allow extrapolation
        )
    else:
        result = usecases_domain_calculator_interpolation(
            input_value=input,
            points=data_points,
            input_key=lambda p: p[0],  # Rank is input
            output_key=lambda p: p[1],  # PP is output
            clamp=True,  # Clamp for stability
        )
    return int(round(result))

@usecases.domain.cache_control.cache_group("performance")
async def rank_for_pp(pp: PP, game_mode: osuGameMode) -> RANK:
    return local(pp, "rank", game_mode)

@usecases.domain.cache_control.cache_group("performance")
async def pp_for_rank(rank: RANK, game_mode: osuGameMode) -> PP:
    return local(rank, "pp", game_mode)

Position = int
TotalScore = int

def position_for_score(
    scores_total_score: TotalScore, data_points: list[tuple[Position, TotalScore]]
) -> Position:
    return int(
        round(
            usecases_domain_calculator_interpolation(
                input_value=scores_total_score,
                points=data_points,
                input_key=lambda p: p[1],
                output_key=lambda p: p[0],
                clamp=False,  # Use extrapolation for values outside data range
            )
        )
    )
