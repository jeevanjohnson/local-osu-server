"""
Use case for fetching rank from osu!daily API.
Handles credential validation, error handling, and client logout on auth failure.
"""

from typing import Literal

import orjson
from aiohttp import ClientSession, ClientTimeout

from adapters import log, log_time
from osuProtocol.server_packets import osuGameMode


async def get_pp_for_rank(rank: int, game_mode: osuGameMode) -> int | None:
    return await get(type="rank", value=rank, game_mode=game_mode)


# @cached_for_five_minutes
async def get_rank_for_pp(pp: int, game_mode: osuGameMode) -> int | None:
    return await get(type="pp", value=pp, game_mode=game_mode)


@log_time
# @cached_for_five_minutes
async def get(
    type: Literal["rank", "pp"], value: int, game_mode: osuGameMode
) -> int | None:
    """
    Fetch rank or PP from osu!daily API for given value and game mode.

    Args:
        value: Value to fetch (rank or PP)
        game_mode: Game mode (osuGameMode enum)

    Returns:
        Rank as integer, or None if credentials are missing/invalid or request fails

    Side effects:
        If credentials are missing/invalid, or if API request fails,
        will log the user out of the client with an explanatory message.
    """

    # http_client = await get_http_client()

    url = "https://osudaily.net/api/pp.php"
    params = {
        "k": api_key,
        "t": type,
        "v": str(value),
        "m": str(game_mode.value),
    }

    print(
        "{url}?{params}".format(
            url=url, params="&".join(f"{k}={v}" for k, v in params.items())
        )
    )

    async with ClientSession() as session:
        async with session.get(
            url,
            params=params,
            timeout=ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            response_text = await response.text()

    if not response_text.strip():
        log.error(
            f"Empty response from osu!daily API for {type} {value} and game mode {game_mode}."
        )
        # await usecases.sessions.restart_client(error_msg)
        return None

    try:
        json = orjson.loads(response_text)
    except orjson.JSONDecodeError:
        log.error(
            f"Failed to decode JSON from osu!daily API response for {type} {value} and game mode {game_mode}. Response text: {response_text}"
        )
        # await usecases.sessions.restart_client(error_msg)
        return None

    # Some responses may decode to null/non-object payloads.
    if not isinstance(json, dict):
        log.warning(
            f"Unexpected osu!daily response payload for {type} {value} and game mode {game_mode}: {json}"
        )
        return None

    # Retry once after API's documented 1 req/s restriction.
    if "error" in json and json["error"] == "Only 1 request per second is authorized":
        log.warning("Rate limited by osu!daily API after retry.")
        return None

    # Check for other API errors (likely credential-related)
    if "error" in json:
        log.error(f"API error from osu!daily: {json.get('error')}")
        # await usecases.sessions.restart_client(error_msg)
        return None

    # Extract rank from response
    if type == "pp":
        if "rank" not in json:
            log.error(
                f"Rank not found in response for pp {value} and game mode {game_mode}. "
                f"Response: {json}"
            )
            # await usecases.sessions.restart_client(error_msg)
            return None

        return int(json["rank"])
    else:
        if "pp" not in json:
            log.error(
                f"PP not found in response for rank {value} and game mode {game_mode}. "
                f"Response: {json}"
            )
            # await usecases.sessions.restart_client(error_msg)
            return None
        return int(json["pp"])
