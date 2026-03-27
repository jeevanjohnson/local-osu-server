# LOS2026 Architecture Refactoring Guide

## Overview

This document addresses key architectural concerns and proposes improvements to decouple components, improve testability, and better match the single-user server design.

---

## 1. Packet Queue Coupling Issue

### Problem

The current `session.packet_queue` approach is tightly coupled with the session model:

```python
# Current (Dirty)
session.packet_queue += some_packet.build()
await sessions.update_current_session(session)  # Persists everything together
```

**Issues:**
- Mixes client state with packet management
- Hard to test packet sending independently
- Couples business logic with session persistence
- Packets should be a separate concern from user session state

### Solution: Separate Client Updates Model

Create a dedicated `ClientUpdates` model to manage outgoing packets:

```python
# models/database/client_updates.py
from pydantic import BaseModel
from datetime import datetime

class ClientUpdate(BaseModel):
    """Represents pending packets to send to the client."""
    user_id: int
    packets: list[bytes] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

**Implementation:**

```python
# repos/client_updates.py
class ClientUpdatesRepository:
    async def get_for_user(self, user_id: int) -> ClientUpdate:
        """Get pending updates for user."""
        
    async def add_packet(self, user_id: int, packet: bytes) -> None:
        """Add packet to user's update queue."""
        
    async def clear(self, user_id: int) -> None:
        """Clear all packets for user (after sending)."""

# usecases/client_notifications.py
async def send_message(recipient_id: int, message: str) -> None:
    """Send a chat message to a client."""
    updates_repo = ClientUpdatesRepository()
    packet = Message(sender="BanchoBot", message=message).build()
    await updates_repo.add_packet(recipient_id, packet)

async def send_friend_update(recipient_id: int, friend_id: int, status: bool) -> None:
    """Send friend status update."""
    updates_repo = ClientUpdatesRepository()
    packet = (PlayerLogOut(friend_id) if not status else BanchoUser(...)).build()
    await updates_repo.add_packet(recipient_id, packet)
```

**In Controller:**

```python
@bancho.post("/")
async def client_request_handler(request: Request, ...):
    # Process incoming packets
    for packet in incoming_packets:
        await PACKET_HANDLERS[packet._id](packet, session)
    
    # Fetch and send all pending updates
    updates = await client_updates_repo.get_for_user(session.user_id)
    response = b''.join(updates.packets)
    
    # Clear the queue
    await client_updates_repo.clear(session.user_id)
    
    # Session is simpler now - just state, no packets
    await usecases.sessions.update_current_session(session)
    
    return Response(content=response)
```

**Benefits:**
- ✅ Decouples packet management from session
- ✅ Clear separation of concerns
- ✅ Easy to test independently
- ✅ Controller is simpler - just reads/flushes
- ✅ Can send packets from anywhere (use cases) without touching session

---

## 2. Cache Registry Pattern

### Problem

Current regex-based cache clearing is vague and error-prone:

```python
# Current (Fragile)
cache.clear_cache_pattern("*bancho*")     # Typos? Silent failures
cache.clear_cache_pattern("*friends*")    # What if pattern doesn't match?
```

**Issues:**
- String patterns are easy to typo
- No compile-time checking
- Hard to see which caches are affected
- Not explicit about intent

### Solution: Cache Registry with Groups

```python
# cache.py - Enhanced with Registry System

class CacheRegistry:
    """Manages groups of related cached functions."""
    
    def __init__(self):
        self.groups: dict[str, list[str]] = {}  # group_name -> [func_names]
        self.cache_instances: dict[str, Cache] = {}  # func_name -> cache instance
    
    def register_function(self, group: str, func_name: str, cache_instance: Cache) -> None:
        """Register a cached function to a group."""
        if group not in self.groups:
            self.groups[group] = []
        self.groups[group].append(func_name)
        self.cache_instances[func_name] = cache_instance
    
    def clear_group(self, group: str) -> int:
        """Clear all caches in a group. Returns count cleared."""
        count = 0
        for func_name in self.groups.get(group, []):
            if func_name in self.cache_instances:
                self.cache_instances[func_name].clear()
                count += 1
        return count
    
    def list_group(self, group: str) -> list[tuple[str, int]]:
        """List all functions in a group with their cache sizes."""
        return [
            (func_name, self.cache_instances[func_name].size)
            for func_name in self.groups.get(group, [])
        ]

CACHE_REGISTRY = CacheRegistry()

def cached_for_five_minutes(group: str = "general"):
    """Decorator with group registration."""
    def decorator(func: F) -> F:
        cache_func = CacheFunction(timedelta(minutes=5))
        wrapped = cache_func.function(func)
        
        # Register to group
        CACHE_REGISTRY.register_function(group, func.__qualname__, cache_func)
        
        return wrapped
    return decorator
```

**Usage:**

```python
# usecases/bancho_scores.py
# @cached_for_five_minutes(group="friend_scores")
async def get_friends_scores_for_beatmap(...): ...

# @cached_for_five_minutes(group="friend_scores")
async def get_score_for_user_on_beatmap(...): ...

# usecases/leaderboards.py
# @cached_for_five_minutes(group="leaderboards")
async def get_leaderboard(...): ...

# usecases/commands.py - Clear specific group
async def add_friend_command(...):
    await usecases.profiles.add_friend(...)
    
    # Clear related caches
    cleared = cache.CACHE_REGISTRY.clear_group("friend_scores")
    log.success(f"Cleared {cleared} friend score caches")

# Or diagnostic use
stats = cache.CACHE_REGISTRY.list_group("leaderboards")
for func_name, size in stats:
    print(f"{func_name}: {size} entries")
```

**Benefits:**
- ✅ Explicit grouping - no magic strings or patterns
- ✅ Compile-time aware (IDEs can help)
- ✅ Easy to see what's in each group
- ✅ No typos affecting cache invalidation
- ✅ Better diagnostics

---

## 3. Orchestrator Layer (Above Use Cases)

### Problem

Multiple use cases are being called together without coordination:

```python
# Controllers are complex - mix of concerns
async def get_leaderboard(...):
    beatmap = await usecases.beatmaps.from_md5(...)
    scores = await usecases.bancho_scores.get_scores_for(...)
    personal_best = await usecases.scores.get_pb_for_user(...)
    # ... controller logic mixed with business logic
```

**Questions:**
- Where does multi-use-case logic live?
- How do we test complex workflows?
- How do we reuse these workflows?

### Solution: Orchestrator/Application Service Layer

```
Controllers (HTTP/Packets) - DTO/Protocol
    ↓
Orchestrators/Services - Multi-use-case workflows  ← NEW LAYER
    ↓
Use Cases - Single business operation, testable
    ↓
Repositories - Data access
```

**Implementation:**

```python
# usecases/orchestrators/__init__.py
"""
Application Services / Orchestrators

These coordinate multiple use cases to accomplish higher-level goals.
They handle workflow logic that spans multiple domains.
They are testable and reusable across controllers.
"""

# usecases/orchestrators/leaderboard_service.py
class LeaderboardService:
    """Orchestrates leaderboard generation."""
    
    async def generate_full_leaderboard(
        self,
        beatmap_md5: str,
        user_id: int,
        game_mode: osuGameMode,
        scoring_algorithm: ScoringAlgorithm,
    ) -> Leaderboard:
        """
        Coordinate multiple use cases to build a complete leaderboard.
        
        Workflow:
        1. Fetch beatmap
        2. Fetch scores from API
        3. Get user's personal best
        4. Rank the scores
        5. Build leaderboard response
        """
        # Use case 1: Get beatmap details
        beatmap = await usecases.beatmaps.from_md5(beatmap_md5)
        if not beatmap:
            raise BeatmapNotFoundError(beatmap_md5)
        
        # Use case 2: Get scores
        scores = await usecases.bancho_scores.get_scores_for(
            beatmap=beatmap,
            game_mode=game_mode,
            scoring_algorithm=scoring_algorithm,
            ranking_type=RankingType.PERFORMANCE,
        )
        
        # Use case 3: Get personal best
        personal_best = await usecases.scores.get_pb_for_user(
            user_id=user_id,
            beatmap_md5=beatmap_md5,
            game_mode=game_mode,
        )
        
        # Orchestrate result
        return Leaderboard(
            beatmap=beatmap,
            scores=scores,
            personal_best=personal_best,
            scoring_algorithm=scoring_algorithm,
        )

# usecases/orchestrators/profile_stats_service.py
class ProfileStatsService:
    """Orchestrates profile stat recalculation."""
    
    async def recalculate_all_stats(
        self,
        profile_name: str,
        server_settings: ServerSettings,
    ) -> Profile:
        """
        Recalculate all stats for all game modes.
        
        Workflow:
        1. Fetch profile
        2. For each game mode: recalculate stats
        3. Update rankings
        4. Return updated profile
        """
        profile = await usecases.profiles.get_profile(profile_name)
        
        for game_mode in osuGameMode:
            await usecases.profiles.recalculate_stats(
                profile_name=profile_name,
                max_combo=0,
                game_mode=game_mode,
                scoring_algorithm=profile.settings.scoring_algorithm,
                server_settings=server_settings,
            )
        
        return await usecases.profiles.get_profile(profile_name)

# usecases/orchestrators/friend_management_service.py
class FriendManagementService:
    """Orchestrates friend list operations."""
    
    async def add_friend_and_notify(
        self,
        profile_name: str,
        friend_user_id: int,
    ) -> None:
        """
        Add friend and notify client.
        
        Workflow:
        1. Add friend to profile
        2. Invalidate friend caches
        3. Queue update packet to client
        """
        # Use case 1: Add friend
        await usecases.profiles.add_friend(profile_name, friend_user_id)
        
        # Use case 2: Clear related caches
        cache.CACHE_REGISTRY.clear_group("friend_scores")
        cache.CACHE_REGISTRY.clear_group("friend_stats")
        
        # Use case 3: Notify client
        friend_status = await usecases.bancho_users.get_friends_client_status(
            user_ids=[friend_user_id],
            game_mode=osuGameMode.STANDARD,
        )
        
        # Queue notification (new pattern)
        current_user_id = 2  # Get from session/context
        await client_notifications.queue_packets(
            user_id=current_user_id,
            packets=friend_status.build(),
        )
```

**In Controllers - Much Simpler:**

```python
# controllers/subdomains/osu.py
from usecases.orchestrators.leaderboard_service import LeaderboardService

@osu.get("/leaderboard/{beatmap_md5}")
@log_time
async def get_leaderboard_handler(
    beatmap_md5: str,
    session: Session,
) -> bytes:
    """Fetch leaderboard - orchestrator handles complexity."""
    leaderboard_service = LeaderboardService()
    
    leaderboard = await leaderboard_service.generate_full_leaderboard(
        beatmap_md5=beatmap_md5,
        user_id=session.user_id,
        game_mode=session.current_game_mode,
        scoring_algorithm=session.settings.scoring_algorithm,
    )
    
    return leaderboard.serialize()
```

**Benefits:**
- ✅ **Clear Intent**: `LeaderboardService.generate_full_leaderboard()` is obvious
- ✅ **Testable**: Mock individual use cases
- ✅ **Reusable**: Any endpoint can call orchestrators
- ✅ **Decouples**: Controllers don't know about internal dependencies
- ✅ **Maintainable**: Workflow logic is in one place
- ✅ **Composable**: Orchestrators can call other orchestrators

---

## 4. Songs Folder Process Alternative

### Problem

Using multiprocessing for songs folder loading has overhead:

```python
# Current - subprocess overhead
process = mp.Process(target=songs_folder.load_all)
process.start()
```

**Issues:**
- Separate Python interpreter overhead
- Memory duplication
- Complex serialization
- Harder to debug

### Solutions

#### Option A: Lazy Loading (Simplest)

```python
# usecases/songs_folder.py
songs_cache: SongsFolder | None = None

# @cached_forever
async def get_songs_folder() -> SongsFolder:
    """Load songs once on first request."""
    global songs_cache
    if songs_cache is None:
        songs_cache = await parse_all_osu_files()
    return songs_cache
```

**Pros:** Simple, no extra processes
**Cons:** First request is slow (blocking)

#### Option B: Threaded Loading (Recommended for Single-User)

```python
# processes/songs_folder.py
import asyncio
import concurrent.futures
from pathlib import Path

class SongsFolder:
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.songs: dict[str, OsuFile] = {}
        self.loaded = asyncio.Event()
    
    async def load_async(self) -> None:
        """Load all songs in background thread pool."""
        loop = asyncio.get_event_loop()
        self.songs = await loop.run_in_executor(
            self.executor,
            self._load_sync,
        )
        self.loaded.set()
    
    def _load_sync(self) -> dict[str, OsuFile]:
        """Synchronous loading - runs in thread."""
        songs = {}
        songs_dir = Path("./songs")
        
        for osu_file in songs_dir.glob("**/*.osu"):
            try:
                song = OsuFile.from_path(osu_file)
                songs[song.beatmap_md5] = song
            except Exception as e:
                log.warning(f"Failed to load {osu_file}: {e}")
        
        return songs
    
    async def wait_ready(self, timeout: float = 60.0) -> None:
        """Wait for songs to be loaded."""
        await asyncio.wait_for(self.loaded.wait(), timeout)
    
    def get_song(self, md5: str) -> OsuFile | None:
        """Get cached song by MD5."""
        return self.songs.get(md5)

# Singleton
SONGS_FOLDER = SongsFolder()

# In startup
async def on_startup():
    await SONGS_FOLDER.load_async()
    log.success("Songs folder loaded in background")

# In handlers
async def get_beatmap_data(beatmap_md5: str):
    await SONGS_FOLDER.wait_ready()  # Wait if not loaded
    song = SONGS_FOLDER.get_song(beatmap_md5)
    return song.difficulty
```

**Pros:**
- ✅ No separate Python interpreter
- ✅ Shared memory (no serialization)
- ✅ Still non-blocking
- ✅ Easy to manage task pool

**Cons:** Less parallelism than multiprocessing (GIL)

#### Option C: Keep Multiprocessing But Optimize

```python
# If you must use multiprocessing
import multiprocessing as mp

class SongsFolder:
    def __init__(self):
        self.ready = mp.Event()
        self.songs_dict = mp.Manager().dict()
        self.process = None
    
    def start_loading(self):
        """Start background process loading."""
        self.process = mp.Process(target=self._load_worker)
        self.process.daemon = True
        self.process.start()
    
    def _load_worker(self):
        """Worker process."""
        songs = self._load_sync()
        self.songs_dict.update(songs)
        self.ready.set()
    
    async def wait_ready(self, timeout=60):
        """Wait for loading to complete."""
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(
            loop.run_in_executor(None, self.ready.wait),
            timeout
        )
```

### Recommendation for Single-User Server

**Use Option B (Threading):**
- Good parallelism for I/O (disk reading)
- No separate interpreter
- Shared memory with main thread
- Simpler than multiprocessing

---

## 5. Sessions for Single-User Server

### Problem

Sessions are designed for concurrent multi-user systems:

```python
# Current - overkill for single-user
class Session(BaseModel):
    user_id: int
    profile_name: str
    is_logged_in: bool
    current_game_mode: osuGameMode
    latest_beatmap: Beatmap | None
    packet_queue: bytes
    # ... 10 more fields
```

**Issues:**
- Designed for cookies/concurrent users
- Overly complex for single-user constraint
- Sessions imply persistence across disconnects
- Should you really persist this?

### Solution: Simplified Global Client State

```python
# models/client/state.py
"""
Global client state for the logged-in user.
Since only one user can be logged in at once, we use a singleton pattern.
This replaces the complex Session model.
"""

from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class ClientState(BaseModel):
    """Represents the current state of the connected client."""
    
    # Authentication
    is_logged_in: bool = False
    profile_name: str | None = None
    user_id: int | None = None
    
    # Current Activity
    current_game_mode: osuGameMode = osuGameMode.STANDARD
    latest_enabled_mods: osuMods = osuMods.NOMOD
    latest_beatmap: Beatmap | None = None
    latest_replay_id: int = 0
    
    # Client Connection
    opened: bool = False
    logged_in_at: datetime | None = None
    
    class Config:
        arbitrary_types_allowed = True

# Singleton instance
CURRENT_CLIENT_STATE = ClientState()

# Optional: persistence to file
async def load_client_state() -> None:
    """Load client state from file on startup."""
    global CURRENT_CLIENT_STATE
    state_file = Path("data/client_state.json")
    
    if state_file.exists():
        data = orjson.loads(state_file.read_bytes())
        CURRENT_CLIENT_STATE = ClientState(**data)

async def save_client_state() -> None:
    """Save client state to file."""
    state_file = Path("data/client_state.json")
    state_file.write_bytes(
        orjson.dumps(CURRENT_CLIENT_STATE.dict())
    )

# On logout - reset
async def logout_client():
    """Handle client logout."""
    CURRENT_CLIENT_STATE.is_logged_in = False
    CURRENT_CLIENT_STATE.profile_name = None
    CURRENT_CLIENT_STATE.user_id = None
    CURRENT_CLIENT_STATE.opened = False
    await save_client_state()
```

**In Controllers - Much Simpler:**

```python
# controllers/subdomains/cho.py
from models.client.state import CURRENT_CLIENT_STATE

@bancho.post("/")
async def client_request_handler(
    request: Request,
    osu_token: str | None = Header(None),
):
    wants_login = osu_token is None
    
    if wants_login:
        # Handle login
        CURRENT_CLIENT_STATE.is_logged_in = True
        CURRENT_CLIENT_STATE.profile_name = login_data["username"]
        CURRENT_CLIENT_STATE.logged_in_at = datetime.now()
        CURRENT_CLIENT_STATE.opened = True
        
        await save_client_state()
        
        return Response(content=login_response.build())
    
    if not CURRENT_CLIENT_STATE.is_logged_in:
        return Response(content=SilentRelog.build())
    
    # Process packets
    incoming_packets = Packets(await request.body())
    for packet in incoming_packets:
        await PACKET_HANDLERS[packet._id](packet)
    
    # Simplified - no session management
    return Response(content=response_packets)
```

**Benefits:**
- ✅ **Matches Architecture**: Single user = single global state
- ✅ **Simpler Code**: No Session creation/lookup/persistence per-request
- ✅ **Obvious Logic**: State is right there
- ✅ **Faster**: No database queries for session
- ✅ **Type-Safe**: Clear what fields exist
- ✅ **Optional Persistence**: Can save/load state if needed

**When to Keep Sessions:**
- Multiple users can be logged in simultaneously
- Need to track disconnects/reconnects
- Building real multi-user server

**For Your Single-User Server:**
- Use global `ClientState`
- Optional file persistence
- Easy to add multi-user later (just convert to Session when needed)

---

## Summary: Architectural Changes

| Issue | Current | Improved |
|-------|---------|----------|
| **Packet Management** | Coupled to Session | Separate `ClientUpdates` model |
| **Cache Clearing** | Regex patterns | `CacheRegistry` with groups |
| **Multi-Use-Case Logic** | Mixed in controllers | `Orchestrator` services layer |
| **Song Loading** | Multiprocess | Thread pool |
| **User State** | Complex `Session` | Simple `ClientState` (singleton) |

---

## Implementation Priority

1. **Start with:** Cache Registry → Quick win, improves all commands
2. **Then:** ClientUpdates → Cleans up packet management
3. **Then:** Orchestrators → Improves testability and reusability
4. **Then:** ClientState → Simplifies all controllers
5. **Finally:** Threading for songs → Performance optimization

---

## Questions?

Each section above has specific code examples. Let me know which you'd like to implement first!
