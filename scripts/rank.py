"""
SCRIPT USED FOR BUILDING THE DATA POINTS FOR THE RANKING SYSTEM.
"""

# import config
# from asyncio import log
import sys

# # from adapters import log
from pathlib import Path

import ossapi

sys.path.append(str(Path(__file__).parent.parent))

import asyncio
import time
from datetime import timedelta
from enum import IntEnum, unique
from pathlib import Path
from typing import TypedDict

import aiohttp
import orjson


@unique
class osuGameMode(IntEnum):
    STANDARD = 0
    TAIKO = 1
    CATCH_THE_BEAT = 2
    MANIA = 3

    def to_api_v2(self) -> ossapi.GameMode:
        return {
            self.STANDARD: ossapi.GameMode.OSU,
            self.TAIKO: ossapi.GameMode.TAIKO,
            self.CATCH_THE_BEAT: ossapi.GameMode.CATCH,
            self.MANIA: ossapi.GameMode.MANIA,
        }[self]

    @classmethod
    def from_osu_file(cls, mode: int) -> "osuGameMode":
        return {0: cls.STANDARD, 1: cls.TAIKO, 2: cls.CATCH_THE_BEAT, 3: cls.MANIA}[
            mode
        ]

    @classmethod
    def from_api_v2(cls, mode: ossapi.GameMode) -> "osuGameMode":
        return {
            ossapi.GameMode.OSU: cls.STANDARD,
            ossapi.GameMode.TAIKO: cls.TAIKO,
            ossapi.GameMode.CATCH: cls.CATCH_THE_BEAT,
            ossapi.GameMode.MANIA: cls.MANIA,
        }[mode]


TOTAL_REGISTERED_USERS = 26_989_484

# Configuration for batching
BATCH_SIZE = 10  # Number of concurrent requests per batch
BATCH_DELAY = 1.0  # Delay in seconds between batches
REQUEST_TIMEOUT = 1.0  # 1 second timeout for each individual request


class Data(TypedDict):
    # pp, rank
    std: list[tuple[int, int]]
    taiko: list[tuple[int, int]]
    catch: list[tuple[int, int]]
    mania: list[tuple[int, int]]


async def main():
    data_points_file = Path("scripts/ranking_data.json")
    if data_points_file.exists():
        data_points_file.unlink()  # Remove existing file to start fresh

    data: Data = {"std": [], "taiko": [], "catch": [], "mania": []}

    ranks_to_cover = [
        *range(1, 101),  # Top 100
        *range(
            1000, 10001, 1000
        ),  # Every 1k from 1k to 10k, ex. 1000, 2000, ..., 10000
        *range(
            10000, 100001, 10000
        ),  # Every 10k from 10k to 100k, ex. 10000, 20000, ..., 100000
        *range(
            100000, 1000001, 100000
        ),  # Every 100k from 100k to 1M, ex. 100000, 200000, ..., 1000000
        *range(
            1000000, TOTAL_REGISTERED_USERS + 1, 500000
        ),  # Every 500k from 1M to total users, ex. 1M, 1.5M, ..., up to total users
    ]

    start_time = time.time()
    # print(f"Starting data collection for ranking system. Total ranks to cover: {len(ranks_to_cover)}")
    # print(f"Using batch size: {BATCH_SIZE}, delay between batches: {BATCH_DELAY} seconds")
    # print(f"Request timeout: {REQUEST_TIMEOUT} second(s)\n")

    client = aiohttp.ClientSession()

    for game_mode in [
        osuGameMode.STANDARD,
        osuGameMode.TAIKO,
        osuGameMode.CATCH_THE_BEAT,
        osuGameMode.MANIA,
    ]:
        for rank in ranks_to_cover:
            print(f"Fetching data point for {game_mode.name} - Rank: {rank}...")

            params = {
                "k": "83ed1b45786e0d7256729dfe717be2b9",
                "t": "pp",
                "v": str(rank),
                "m": str(game_mode.value),
            }

            try:
                await asyncio.sleep(1)  # Sleep briefly to avoid hitting rate limits
                print(
                    "{url}?{params}".format(
                        url="https://osudaily.net/api/pp.php",
                        params="&".join(f"{k}={v}" for k, v in params.items()),
                    )
                )

                async with client.get(
                    "https://osudaily.net/api/pp.php",
                    params=params,
                ) as response:
                    if response.status == 200:
                        response_text = await response.text()

                json = orjson.loads(response_text)

                pp = int(json["pp"])
                data_point = (pp, rank)

                if game_mode == osuGameMode.STANDARD:
                    data["std"].append(data_point)
                elif game_mode == osuGameMode.TAIKO:
                    data["taiko"].append(data_point)
                elif game_mode == osuGameMode.CATCH_THE_BEAT:
                    data["catch"].append(data_point)
                else:
                    data["mania"].append(data_point)
            except Exception as e:
                print(
                    f"Error fetching data point for {game_mode.name} - Rank: {rank}: {e}"
                )
                continue

    for game_mode in [
        osuGameMode.STANDARD,
        osuGameMode.TAIKO,
        osuGameMode.CATCH_THE_BEAT,
        osuGameMode.MANIA,
    ]:
        if game_mode == osuGameMode.STANDARD:
            mode_key = "std"
        elif game_mode == osuGameMode.TAIKO:
            mode_key = "taiko"
        elif game_mode == osuGameMode.CATCH_THE_BEAT:
            mode_key = "catch"
        else:
            mode_key = "mania"

        data[mode_key].append((0, TOTAL_REGISTERED_USERS))
        print(
            f"Added data point for {mode_key} - Rank: {TOTAL_REGISTERED_USERS}, PP: 0"
        )

    # Save data to file
    print(f"\n{'=' * 50}")
    print("Saving data...")
    print(f"{'=' * 50}")

    try:
        with data_points_file.open("wb+") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    except:
        with open("./temp.json", "wb+") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    print(f"Data points saved to {data_points_file}")

    elapsed_seconds = time.time() - start_time
    elapsed_time = timedelta(seconds=elapsed_seconds)
    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60
    seconds = elapsed_seconds % 60

    print(
        f"\nData collection completed in {int(hours)} hours, {int(minutes)} minutes, {seconds:.2f} seconds."
    )
    print(f"Total data points collected: {sum(len(v) for v in data.values())}")  # type: ignore


if __name__ == "__main__":
    asyncio.run(main())
