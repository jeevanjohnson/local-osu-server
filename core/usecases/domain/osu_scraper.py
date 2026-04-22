from core.models.domain.gameplay.game_mode import GameMode
from core.repositories.osu_scraper import OsuScraperRepository
from core.models.database.osu_scraper import SnapShot
from typing import TypedDict
from datetime import datetime

class GetRecentSnapshotResponse(TypedDict):
    snapshot: SnapShot
    timestamp: datetime

class CreateNewSnapshotResponse(TypedDict):
    snapshot: SnapShot
    timestamp: datetime

def get_recent_snapshot() -> GetRecentSnapshotResponse:
    print(f"[OSU_SCRAPER] Getting recent snapshot...")
    osu_scraper_repo = OsuScraperRepository()
    osu_scraper_state = osu_scraper_repo.get_state()
    
    print(f"[OSU_SCRAPER] Available snapshots: {len(osu_scraper_state.snapshots)}")
    
    timestamps = list(osu_scraper_state.snapshots.keys())
    if not timestamps:
        print(f"[OSU_SCRAPER] ❌ No snapshots found! Creating empty snapshot")
        now = datetime.now()
        osu_scraper_state.snapshots[now] = SnapShot()
        osu_scraper_state = osu_scraper_repo.update_state(osu_scraper_state)
        snapshot = osu_scraper_state.snapshots[now]
        print(f"[OSU_SCRAPER] Created empty snapshot - osu: {len(snapshot.osu)}, taiko: {len(snapshot.taiko)}, catch: {len(snapshot.catch)}, mania: {len(snapshot.mania)}")
        return {
            "snapshot": snapshot,
            "timestamp": now,
        }

    # Find the most recent snapshot that has DATA, not just the most recent timestamp
    # (The scraper might be creating a new empty snapshot while running)
    recent_timestamp = None
    for timestamp in sorted(timestamps, reverse=True):
        snapshot = osu_scraper_state.snapshots[timestamp]
        # Check if this snapshot has any data
        if snapshot.osu or snapshot.taiko or snapshot.catch or snapshot.mania:
            recent_timestamp = timestamp
            break
    
    # Fallback: if all snapshots are empty, use the most recent one
    if recent_timestamp is None:
        recent_timestamp = max(timestamps)
        print(f"[OSU_SCRAPER] ⚠️  All snapshots are empty! Using most recent timestamp: {recent_timestamp}")
    
    snapshot = osu_scraper_state.snapshots[recent_timestamp]
    print(f"[OSU_SCRAPER] Using snapshot from {recent_timestamp}")
    print(f"[OSU_SCRAPER] Data points - osu: {len(snapshot.osu)}, taiko: {len(snapshot.taiko)}, catch: {len(snapshot.catch)}, mania: {len(snapshot.mania)}")
    
    return {
        "snapshot": snapshot,
        "timestamp": recent_timestamp,
    }

def create_new_snapshot() -> CreateNewSnapshotResponse:
    osu_scraper_repo = OsuScraperRepository()
    osu_scraper_state = osu_scraper_repo.get_state()
    
    now = datetime.now()
    new_snapshot = SnapShot()
    osu_scraper_state.snapshots[now] = new_snapshot
    osu_scraper_state = osu_scraper_repo.update_state(osu_scraper_state)

    return {
        "snapshot": osu_scraper_state.snapshots[now],
        "timestamp": now,
    }

def update_snapshot(timestamp: datetime, snapshot: SnapShot) -> SnapShot:
    osu_scraper_repo = OsuScraperRepository()
    osu_scraper_state = osu_scraper_repo.get_state()
    osu_scraper_state.snapshots[timestamp] = snapshot
    osu_scraper_state = osu_scraper_repo.update_state(osu_scraper_state)

    return osu_scraper_state.snapshots[timestamp]