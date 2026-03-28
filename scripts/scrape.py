"""
SCRIPT USED FOR BUILDING THE DATA POINTS FOR THE RANKING SYSTEM.
"""

# import config
# from asyncio import log
import sys

# # from adapters import log
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent))


import aiohttp
import json
import asyncio
import math
from bs4 import BeautifulSoup
from enum import Enum
from datetime import datetime

class GameMode(Enum):
    OSU = "osu"
    TAIKO = "taiko"
    CATCH = "fruits"
    MANIA = "mania"

Rank = int
PP = int

Point = tuple[Rank, PP]

DATA_POINTS: dict[str, list[Point]] = {
    GameMode.OSU.value: [],
    GameMode.TAIKO.value: [],
    GameMode.CATCH.value: [],
    GameMode.MANIA.value: [],
}

URL = "https://osu.ppy.sh/rankings/{mode}/global/performance?filter=all&page={page}#scores"

TIME_STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

async def total_registered_users() -> int:
    global DATA_POINTS, TIME_STAMP

    async with aiohttp.ClientSession() as http:
        async with http.get("https://osu.ppy.sh/") as response:
            if response.status != 200:
                print(f"Failed to fetch total registered users, status code: {response.status}")
                return 0

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            
            user_count_element = soup.select_one('[class="landing-hero__info"]')
            assert user_count_element is not None and user_count_element.string is not None, (
                "Could not find user count element on the page"
            )

            registered_users_str, _ = user_count_element.string.split("", maxsplit=1)

            registered_users = int(
                registered_users_str.replace("\n", "").replace(",", "").strip()
            )

            return registered_users


async def get_50_ranks(page: int, game_mode: GameMode) -> None:
    global DATA_POINTS, TIME_STAMP

    rank_offset = (page - 1) * 50
    async with aiohttp.ClientSession() as http:
        async with http.get(URL.format(mode=game_mode.value, page=page)) as response:
            if response.status != 200:
                print(f"Failed to fetch page {page} for mode {game_mode.value}, status code: {response.status}")
                return

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            
            rank_rows = soup.select('[class="ranking-page-table__column"]')

            pp = [
                int(row.string.replace("\n", "").replace(",", "").strip()) 
                for row in rank_rows if row.string and "#" not in row.string
            ]

            for i, pp_value in enumerate(pp):
                DATA_POINTS[game_mode.value].append(
                    (rank_offset + i + 1, pp_value)
                )

                # print(f"Added data point: rank={rank_offset + i + 1}, pp={pp_value} for mode {game_mode.value}")
        
        print(f"Fetched page {page} for mode {game_mode.value}")

        with open(f"{TIME_STAMP}.json", "w") as f:
            f.write(
                json.dumps(DATA_POINTS, indent=4)
            )

async def main():
    global DATA_POINTS, TIME_STAMP
    
    pages = 200

    for mode in GameMode:
        for page in range(1, pages + 1):
            while True:
                try:
                    await get_50_ranks(page, mode)
                    await asyncio.sleep(2)  # Sleep for 2 seconds between requests to avoid overwhelming the server
                    break
                except Exception as e:
                    print(f"Error fetching page {page} for mode {mode.value}: {e}")
                    print("Retrying in 5 seconds...")
                    await asyncio.sleep(5)
            
            print(f"Completed {page}/{pages} for mode {mode.value}")
    
    try:
        total_users = await total_registered_users()
        print(f"Total registered users: {total_users}")
    except Exception as e:
        print(f"Error fetching total registered users: {e}")
        total_users = 27_001_016 # fallback value
    
    # Generate synthetic data points to fill the gap between rank 10k and total users
    # Parametrically adjust the decay rate so that the curve naturally satisfies:
    # 1.5k PP ≈ 800k rank (a known real-world osu! relationship)
    for mode in GameMode:
        data_points = DATA_POINTS[mode.value]
        
        if len(data_points) >= 100:
            # Use the last real data point as base for synthetic generation
            # This ensures synthetic PP values never exceed the real data
            last_rank = data_points[-1][0]
            last_pp = data_points[-1][1]
            
            # Target anchor point: what we know from actual osu! data
            TARGET_PP = 1500
            TARGET_RANK = 800_000
            
            # Calculate the decay rate that would naturally reach the target
            # Using exponential model: pp = last_pp * e^(decay_rate * (rank - last_rank))
            # At target: TARGET_PP = last_pp * e^(decay_rate * (TARGET_RANK - last_rank))
            # Solving: decay_rate = ln(TARGET_PP / last_pp) / (TARGET_RANK - last_rank)
            
            if last_pp > 0 and last_pp > TARGET_PP:
                decay_per_rank_log = math.log(TARGET_PP / last_pp) / (TARGET_RANK - last_rank)
            else:
                decay_per_rank_log = -0.000001  # fallback
            
            print(f"Mode {mode.value}: Adjusted decay rate to satisfy anchor point")
            print(f"  Base point (rank {last_rank}): {last_pp} PP")
            print(f"  Decay rate: {decay_per_rank_log:.8f} per rank")
            
            # Verify the target will be reached
            verify_pp = last_pp * math.exp(decay_per_rank_log * (TARGET_RANK - last_rank))
            print(f"  Verification: {TARGET_RANK:,} rank → {verify_pp:.0f} PP (target: {TARGET_PP})")
            
            # Generate synthetic points using the adjusted decay rate
            synthetic_points = []
            current_rank = last_rank
            
            while current_rank < total_users:
                # Increase rank by 50% each iteration
                current_rank = int(current_rank * 1.5)
                if current_rank >= total_users:
                    current_rank = total_users
                
                # Calculate PP at this rank using the adjusted exponential decay
                rank_delta_from_base = current_rank - last_rank
                current_pp = int(last_pp * math.exp(decay_per_rank_log * rank_delta_from_base))
                current_pp = max(0, current_pp)
                
                if current_pp > 0:
                    synthetic_points.append((current_rank, current_pp))
                
                if current_rank >= total_users:
                    break
            
            # Merge synthetic points with real data and sort
            data_points.extend(synthetic_points)
            
            # Add boundary anchor: 0 PP = all remaining users (total_users registered)
            # This represents the absolute bottom - no PP contribution at all
            data_points.append((total_users, 0))
            
            DATA_POINTS[mode.value] = sorted(data_points, key=lambda p: p[0])
            
            print(f"  Added {len(synthetic_points)} synthetic points")
            if DATA_POINTS[mode.value]:
                print(f"  Final data range: rank {DATA_POINTS[mode.value][0][0]} to {DATA_POINTS[mode.value][-1][0]:,}")
                print(f"  Final PP range: {DATA_POINTS[mode.value][-1][1]} to {DATA_POINTS[mode.value][0][1]} PP")
            print()

    with open(f"{TIME_STAMP}.json", "w") as f:
        f.write(
            json.dumps(DATA_POINTS, indent=4)
        )
    
    print(f"Data collection complete. File: {TIME_STAMP}.json")

if __name__ == "__main__":
    asyncio.run(main())