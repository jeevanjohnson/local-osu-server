from typing import Literal

import adapters.osu_daily
from adapters import log
from models.domain.gameplay import osuGameMode

from .linear_interpolation import linear_interpolation

PP = int
RANK = int


# TODO: Make a script that gets data points & then these functions can just read from a file instead of hardcoding these values


# @cached_forever
def local(
    input: PP | RANK, output_type: Literal["pp", "rank"], game_mode: osuGameMode
) -> RANK | PP:
    DATA_POINTS: list[tuple[PP, RANK]]
    if game_mode == osuGameMode.STANDARD:
        # last updated: 3/22/2026
        DATA_POINTS = [
            (33_358, 1),
            (12_211, 2451),
            (10_749, 4951),
            (10_010, 7451),
            (9_444, 9951),
            (5133, 96478),
            (937, 918194),
            (611, 1_171_307),
            (0, 26_971_582),
        ]
    else:
        raise NotImplementedError(
            f"Local rank estimation not implemented for game mode {game_mode}"
        )

    result = linear_interpolation(
        input_value=input,
        points=DATA_POINTS,
        input_key=lambda p: p[0] if output_type == "rank" else p[1],
        output_key=lambda p: p[1] if output_type == "rank" else p[0],
    )
    return int(round(result))


# @cached_forever
async def rank_for_pp(pp: PP, game_mode: osuGameMode) -> RANK:
    """
    Fetch rank for given PP value using osu!daily API.

    Delegates to usecases.osu_daily.get_rank_for_pp which handles:
    - Credential validation
    - API communication
    - Error handling and client logout on auth failure

    Returns:
        Rank as integer (defaults to 9999 if fetch fails)
    """
    if pp < 700:  # osu!daily returns null for ranks below ~700pp
        # Linear interpolation for fetching this value
        return local(pp, "rank", game_mode)

    rank = await adapters.osu_daily.get_rank_for_pp(pp, game_mode)

    if rank is not None:
        return rank

    # rank for osu!daily isn't working (could be due to missing/invalid credentials or API error)
    # retrive rough estimate using local interpolation of known PP->rank points
    log.warning(
        f"Falling back to local rank estimation for pp={pp} due to osu!daily API failure or missing credentials."
    )

    return local(pp, "rank", game_mode)


# @cached_forever
async def pp_for_rank(rank: RANK, game_mode: osuGameMode) -> PP:
    """
    Fetch PP for given rank using osu!daily API.

    Delegates to usecases.osu_daily.get_pp_for_rank which handles:
    - Credential validation
    - API communication
    - Error handling and client logout on auth failure

    Returns:
        PP as integer (defaults to 0 if fetch fails)
    """
    pp = await adapters.osu_daily.get_pp_for_rank(rank, game_mode)

    if pp is not None:
        return pp

    log.warning(
        f"Falling back to local PP estimation for rank={rank} due to osu!daily API failure or missing credentials."
    )
    return local(rank, "pp", game_mode)


Position = int
TotalScore = int


# @cached_forever
def position_for_score(
    scores_total_score: TotalScore, data_points: list[tuple[Position, TotalScore]]
) -> Position:
    return int(
        round(
            linear_interpolation(
                input_value=scores_total_score,
                points=data_points,
                input_key=lambda p: p[1],
                output_key=lambda p: p[0],
            )
        )
    )
