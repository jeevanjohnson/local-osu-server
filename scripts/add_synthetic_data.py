"""
SCRIPT TO ADD SYNTHETIC DATA POINTS TO AN EXISTING SNAPSHOT.

Takes a snapshot JSON file with real data (top 10k users per mode)
and generates synthetic data points to fill the gap up to total_users,
using a parametrically adjusted exponential decay model.

The decay rate is calculated to anchor the curve at:
    1500 PP ≈ 800,000 rank
"""

import json
import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from enum import Enum


class GameMode(Enum):
    OSU = "osu"
    TAIKO = "taiko"
    CATCH = "fruits"
    MANIA = "mania"


def enhance_snapshot(
    snapshot_path: str, output_path: str = None, total_users: int = 27_001_016
):
    """
    Load a snapshot, add synthetic data points, and save the enhanced version.

    Args:
        snapshot_path: Path to the existing snapshot JSON file
        output_path: Path to save the enhanced snapshot (defaults to snapshot path)
        total_users: Total number of registered users to generate data for
    """

    # Load existing snapshot
    with open(snapshot_path, "r") as f:
        data = json.load(f)

    print(f"Loaded snapshot: {snapshot_path}")
    print(f"Total users target: {total_users:,}")
    print()

    # Parametric targets (osu! standard)
    TARGET_PP = 1500
    TARGET_RANK = 800_000

    # Process each game mode
    for mode_str in [
        GameMode.OSU.value,
        GameMode.TAIKO.value,
        GameMode.CATCH.value,
        GameMode.MANIA.value,
    ]:
        if mode_str not in data:
            print(f"Mode {mode_str}: NOT FOUND in snapshot, skipping")
            continue

        data_points = data[mode_str]

        if len(data_points) < 100:
            print(
                f"Mode {mode_str}: Only {len(data_points)} points (need at least 100), skipping"
            )
            continue

        print(f"Mode {mode_str}:")
        print(f"  Real data points: {len(data_points)}")
        print(f"  Rank range: {data_points[0][0]} to {data_points[-1][0]}")
        print(f"  PP range: {data_points[0][1]} to {data_points[-1][1]}")

        # Use the last real data point as base for synthetic generation
        # This ensures synthetic PP values never exceed the real data
        last_rank = data_points[-1][0]
        last_pp = data_points[-1][1]

        # Calculate decay rate to hit target anchor, working backwards from last real point
        if last_pp > 0 and last_pp > TARGET_PP:
            decay_per_rank_log = math.log(TARGET_PP / last_pp) / (
                TARGET_RANK - last_rank
            )
        else:
            decay_per_rank_log = -0.000001

        print(f"  Base point (rank {last_rank}): {last_pp} PP")
        print(f"  Decay rate: {decay_per_rank_log:.8f} per rank")

        # Verify target will be reached
        verify_pp = last_pp * math.exp(decay_per_rank_log * (TARGET_RANK - last_rank))
        print(
            f"  Verification: {TARGET_RANK:,} rank → {verify_pp:.0f} PP (target: {TARGET_PP})"
        )

        # Generate synthetic points
        synthetic_points = []
        current_rank = last_rank

        while current_rank < total_users:
            # Increase rank by 50% each iteration
            current_rank = int(current_rank * 1.5)
            if current_rank >= total_users:
                current_rank = total_users

            # Calculate PP at this rank using the adjusted exponential decay
            rank_delta_from_base = current_rank - last_rank
            current_pp = int(
                last_pp * math.exp(decay_per_rank_log * rank_delta_from_base)
            )
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

        data[mode_str] = sorted(data_points, key=lambda p: p[0])

        print(f"  Added {len(synthetic_points)} synthetic points")
        print(
            f"  Final range: rank {data[mode_str][0][0]} to {data[mode_str][-1][0]:,}"
        )
        print(f"  Final PP range: {data[mode_str][-1][1]} to {data[mode_str][0][1]} PP")
        print()

    # Save enhanced snapshot
    if output_path is None:
        output_path = snapshot_path

    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Enhanced snapshot saved to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_synthetic_data.py <snapshot_path> [output_path]")
        print()
        print("Example:")
        print(
            "  python add_synthetic_data.py usecases/domain/calculator/snapshots/20260328_033609.json"
        )
        print("  python add_synthetic_data.py input.json output_enhanced.json")
        sys.exit(1)

    snapshot_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    enhance_snapshot(snapshot_path, output_path)
