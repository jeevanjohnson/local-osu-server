"""
Use case for fetching rank from osu!daily API.
Handles credential validation, error handling, and client logout on auth failure.
"""

from adapters.app_logger import app_logger
import orjson
from aiohttp import ClientSession, ClientTimeout
from usecases.providers.osu_daily import (
    OsuDailyCredentialsError,
    get_osu_daily_api_key,
)
from osuProtocol.server_packets import osuGameMode


async def get_rank_for_pp(pp: int, game_mode: osuGameMode) -> int | None:
    """
    Fetch rank from osu!daily API for given PP and game mode.
    
    Args:
        pp: Performance points value
        game_mode: Game mode (osuGameMode enum)
        
    Returns:
        Rank as integer, or None if credentials are missing/invalid or request fails
        
    Side effects:
        If credentials are missing/invalid, or if API request fails,
        will log the user out of the client with an explanatory message.
    """
    try:
        # Check if API key exists
        api_key = await get_osu_daily_api_key()
    except OsuDailyCredentialsError as error:
        app_logger.warning(f"osu!daily credentials error: {error}")
        # await usecases.sessions.restart_client(str(error))
        return None

    try:
        # http_client = await get_http_client()

        url = "https://osudaily.net/api/pp.php"
        params = {
            "k": api_key,
            "t": "pp",
            "v": str(pp),
            "m": str(game_mode.value),
        }

        # app_logger.log(
        print(f"Requesting osu!daily rank: {url}?k={params['k']}&t=pp&v={params['v']}&m={params['m']}")
        # )

        async with ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                response_text = await response.text()

        if not response_text.strip():
            app_logger.error(
                f"Empty response from osu!daily API for pp {pp} and game mode {game_mode}"
            )
            # await usecases.sessions.restart_client(error_msg)
            return None

        try:
            json = orjson.loads(response_text)
        except orjson.JSONDecodeError:
            app_logger.error(
                f"Non-JSON response from osu!daily API for pp {pp} and game mode {game_mode}: {response_text!r}"
            )
            # await usecases.sessions.restart_client(error_msg)
            return None

        # Some responses may decode to null/non-object payloads.
        if not isinstance(json, dict):
            app_logger.warning(
                f"Unexpected osu!daily response payload for pp {pp} and game mode {game_mode}: {json}"
            )
            return None

        # Retry once after API's documented 1 req/s restriction.
        if "error" in json and json["error"] == "Only 1 request per second is authorized":
            app_logger.warning("Rate limited by osu!daily API after retry.")
            return None
        
        # Check for other API errors (likely credential-related)
        if "error" in json:
            app_logger.error(f"API error from osu!daily: {json.get('error')}")
            # await usecases.sessions.restart_client(error_msg)
            return None

        # Extract rank from response
        if "rank" not in json:
            app_logger.error(
                f"Rank not found in response for pp {pp} and game mode {game_mode}. "
                f"Response: {json}"
            )
            # await usecases.sessions.restart_client(error_msg)
            return None

        return int(json["rank"])

    except Exception as error:
        app_logger.error(
            f"Unexpected error while fetching rank for pp {pp}: {type(error).__name__}: {error}"
        )
        # await usecases.sessions.restart_client(
        #     "Network error while fetching rank. Please try again later."
        # )
        return None
