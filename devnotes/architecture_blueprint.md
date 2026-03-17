# Architecture Blueprint — Score Sync, Async Leaderboards, Beatmap Resolver
> Date: 3.17.2026  
> This document is **interfaces, DTOs, and method signatures only** — no implementations.  
> Every section maps to an exact file so implementation is mechanical.

---

## Overview of new/changed files

| Action   | File                                  | Purpose                                          |
|----------|---------------------------------------|--------------------------------------------------|
| NEW      | `models/beatmap_cache.py`             | `BeatmapInfo` DTO + `BeatmapCacheEntry` alias    |
| NEW      | `models/osu_client.py`                | DTOs for osu! executable/cfg/song-path discovery |
| MODIFY   | `models/database/server_settings.py`  | Add optional songs path override field           |
| MODIFY   | `constants.py`                        | Add `BEATMAP_CACHE_FILE` path constant           |
| NEW      | `repositories/beatmap_cache.py`       | Read/write `beatmap_cache.json`                  |
| NEW      | `repositories/songs_index.py`         | Glob local Songs folder for `.osu` files         |
| NEW      | `usecases/osu_client_discovery.py`    | Auto-detect osu! install + cfg + Songs folder    |
| NEW      | `usecases/providers/__init__.py`      | Package marker + shared `get_ossapi_async()`     |
| NEW      | `usecases/providers/lazer_scores.py`  | Async lazer score fetching + normalization       |
| NEW      | `usecases/providers/stable_scores.py` | Sync v1 score fetching wrapped in thread         |
| NEW      | `usecases/beatmap_resolver.py`        | cache → local .osu → remote API fallback chain   |
| NEW      | `usecases/score_sync.py`              | Identity key, conflict resolution, merge+rank    |
| NEW      | `usecases/leaderboards.py`            | Single orchestration entrypoint                  |
| MODIFY   | `usecases/beatmaps.py`                | `get_beatmap` delegates to `BeatmapResolver`     |
| MODIFY   | `controllers/subdomains/osu.py`       | `get_leaderboard` becomes thin parse+serialize   |

---

## 1. `models/beatmap_cache.py` (NEW)

```python
from typing import TypedDict

class BeatmapInfo(TypedDict):
    """
    Internal DTO used everywhere a beatmap is referenced.
    Replaces direct ossapi.Beatmap usage so callers survive
    cache/local/remote without knowing the source.
    """
    beatmap_id: int
    beatmapset_id: int
    md5: str
    artist_unicode: str
    title_unicode: str
    version: str          # difficulty name
    max_combo: int | None
    ranked_status: int    # raw ossapi.RankStatus.value int
    mode: int             # osuGameMode.value int

# What gets written to beatmap_cache.json — same shape as BeatmapInfo
BeatmapCacheEntry = BeatmapInfo
```

**Why:** `ossapi.Beatmap` is a pydantic model you can't construct manually. By having
your own flat TypedDict you can build a `BeatmapInfo` from cache JSON, from a parsed
`.osu` header, *and* from an API response, all with the same return type.

---

## 2. `models/osu_client.py` (NEW)

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class OsuClientPaths:
    """
    Resolved paths from a live osu! process.
    """
    process_id: int
    exe_path: Path
    install_dir: Path
    cfg_path: Path
    songs_path: Path

@dataclass
class OsuCfgValues:
    """
    Minimal parsed values from osu!<username>.cfg.
    """
    beatmap_directory: str | None
```

---

## 3. `models/database/server_settings.py` (MODIFY)

```python
class ServerSettings(TypedDict):
    osu_api_key_v1: str | None
    osu_api_v2_client_id: str | None
    osu_api_v2_client_secret: str | None
    osu_songs_path_override: str | None    # NEW — optional manual override
```

**Why:** Auto-discovery should be the default. A manual path is still useful as an
escape hatch if process detection fails, if multiple installs exist, or if osu! is not
running yet.

---

## 4. `constants.py` (MODIFY — add one line)

```python
BEATMAP_CACHE_FILE = DATA_FOLDER / "beatmap_cache.json"
```

---

## 5. `repositories/beatmap_cache.py` (NEW)

```python
from pathlib import Path
from models.beatmap_cache import BeatmapCacheEntry
from database.jsonfile import JsonFile

class BeatmapCacheRepository:
    """
    Persists resolved beatmap metadata to avoid hitting the API repeatedly.
    JSON structure:
        {
            "by_md5":  { "<md5>":  BeatmapCacheEntry, ... },
            "by_id":   { "<id>":   BeatmapCacheEntry, ... }
        }
    """
    def __init__(self, path: Path) -> None: ...

    def get_by_md5(self, md5: str) -> BeatmapCacheEntry | None: ...
    def get_by_id(self, beatmap_id: int) -> BeatmapCacheEntry | None: ...
    def put(self, entry: BeatmapCacheEntry) -> None:
        """Writes under both keys atomically."""
        ...
```

---

## 6. `repositories/songs_index.py` (NEW)

```python
from pathlib import Path

class SongsIndexRepository:
    """
    Scans the local osu! Songs folder for .osu files.
    Uses pathlib.Path.rglob("*.osu") — fast and lazy.
    """
    def __init__(self, songs_path: Path) -> None: ...

    def find_osu_file_by_md5(self, md5: str) -> Path | None:
        """
        rglob all *.osu files, md5-hash each, return first match.
        Cache the glob results in-memory per resolver lifetime to avoid
        re-scanning on every request.
        """
        ...

    def find_osu_file_by_id(self, beatmap_id: int) -> Path | None:
        """
        rglob all *.osu files, parse 'BeatmapID:' line from header,
        return first match. Same in-memory cache applies.
        """
        ...

    @staticmethod
    def parse_osu_header(path: Path) -> dict[str, str]:
        """
        Reads only the [General] and [Metadata] sections of a .osu file
        to extract: Title, TitleUnicode, Artist, ArtistUnicode, Creator,
        Version, BeatmapID, BeatmapSetID, Mode.
        Stops reading at [HitObjects] to keep it fast.
        """
        ...
```

**Why rglob + header parse instead of a pre-built index:** Your Songs folder can contain
thousands of files. A pre-built index would need invalidation logic. A lazy per-request
scan with an in-memory memo inside a single resolver lifetime (one HTTP request) is
simpler and still faster than a network call.

---

## 7. `usecases/osu_client_discovery.py` (NEW)

```python
from pathlib import Path
import psutil

from models.osu_client import OsuClientPaths, OsuCfgValues

class OsuClientDiscovery:
    """
    Resolves osu! Songs path without asking the user.
    Priority:
      1. running osu!.exe process
      2. osu!<username>.cfg BeatmapDirectory value
      3. default 'Songs' under install dir
    """

    def find_running_osu_process(self) -> psutil.Process | None:
        """
        Returns first process whose executable name matches osu!.exe.
        """
        ...

    def resolve_paths_from_process(self, process: psutil.Process) -> OsuClientPaths | None:
        """
        exe_path = process.exe()
        install_dir = exe_path.parent
        cfg_path = _find_user_cfg(install_dir)
        songs_path = _resolve_songs_path(install_dir, cfg_path)
        """
        ...

    def parse_cfg(self, cfg_path: Path) -> OsuCfgValues:
        """
        Lightweight key-value parser for osu! cfg files.
        Reads BeatmapDirectory only.
        """
        ...

    def discover_songs_path(self) -> Path | None:
        """
        High-level method used by resolver/service wiring.
        Returns None when osu! is not running or files are inaccessible.
        """
        ...

    @staticmethod
    def _find_user_cfg(install_dir: Path) -> Path | None:
        """
        Finds osu!*.cfg in install_dir and returns best candidate.
        Prefer newest modified file.
        """
        ...

    @staticmethod
    def _resolve_songs_path(install_dir: Path, cfg_path: Path | None) -> Path:
        """
        If BeatmapDirectory exists in cfg:
          - absolute path -> use as-is
          - relative path -> install_dir / BeatmapDirectory
        Else fallback to install_dir / "Songs".
        """
        ...
```

**Why:** This removes manual setup friction entirely for most users. It also mirrors
real client state, so if BeatmapDirectory is customized, your resolver follows it.

---

## 8. `usecases/providers/__init__.py` (NEW)

```python
from ossapi import OssapiAsync, OssapiV1

async def get_ossapi_async() -> OssapiAsync:
    """
    Reads credentials from ServerSettingsRepository and constructs OssapiAsync.
    Raises ApiV2CredentialsError if credentials are absent or invalid.
    Single source of truth — replaces the duplicated get_ossapi() in
    usecases/scores.py and usecases/beatmaps.py.
    """
    ...

def get_ossapi_v1() -> OssapiV1:
    """
    Same pattern as above for v1.
    Replaces the duplicated get_ossapi_v1() in usecases/scores.py.
    """
    ...
```

**Why centralise here:** Currently `get_ossapi()` is copy-pasted in both
`usecases/scores.py` and `usecases/beatmaps.py`. One shared helper in `providers/`
is the single correct place to construct API clients.

---

## 9. `usecases/providers/lazer_scores.py` (NEW)

```python
from ossapi import OssapiAsync
from ossapi.enums import RankingType, GameMode
from osuProtocol.server_packets import osuGameMode, osuMods
from osuProtocol.client_web import Scores, LazerScore, LegacyScore as ClientLegacyScore

class LazerScoreProvider:
    def __init__(self, api: OssapiAsync) -> None: ...

    async def fetch(
        self,
        beatmap_id: int,
        game_mode: osuGameMode,
        limit: int,
        legacy_only: bool,
        mods: osuMods | None = None,
        beatmap_max_combo: int = 0,
    ) -> Scores | None:
        """
        Calls api.beatmap_scores() with legacy_only flag.
        Normalises each ossapi Score into ClientLegacyScore or LazerScore
        via _normalize_score() and appends to a Scores list.
        """
        ...

    @staticmethod
    def _normalize_score(
        score,                   # ossapi.Score
        legacy_only: bool,
        beatmap_max_combo: int,
    ) -> ClientLegacyScore | LazerScore:
        """
        Contains all the isinstance/field-mapping logic currently duplicated
        between get_scores_for_beatmap_id and get_scores_for_beatmap_md5.
        """
        ...
```

**Why:** `get_scores_for_beatmap_id` and `get_scores_for_beatmap_md5` in
`usecases/scores.py` are 95% identical — the only difference is which lookup key
is used. A single provider collapses them into one place.

---

## 10. `usecases/providers/stable_scores.py` (NEW)

```python
import asyncio
from ossapi import OssapiV1
from osuProtocol.client_web import Scores, LegacyScore as ClientLegacyScore

class StableScoreProvider:
    def __init__(self, api: OssapiV1) -> None: ...

    async def fetch(
        self,
        beatmap_id: int,
        beatmap_max_combo: int = 0,
    ) -> Scores | None:
        """
        Wraps the blocking OssapiV1.get_scores() call in asyncio.to_thread()
        so it doesn't stall the event loop.
        Normalises each LegacyScore into ClientLegacyScore via _normalize_score().
        """
        ...

    @staticmethod
    def _normalize_score(
        score,                  # ossapi.ossapi.Score (v1)
        beatmap_max_combo: int,
    ) -> ClientLegacyScore:
        """
        Contains the assert-heavy mapping logic currently duplicated between
        get_legacy_scores_for_beatmap_id and get_legacy_scores_for_beatmap_md5.
        """
        ...
```

**Why `asyncio.to_thread`:** OssapiAsync only covers API v2. OssapiV1 is sync-only.
Rather than blocking the whole event loop you offload it to a thread, which lets
lazer and stable fetches run concurrently with `asyncio.gather`.

---

## 11. `usecases/beatmap_resolver.py` (NEW)

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from ossapi import OssapiAsync

from models.beatmap_cache import BeatmapInfo
from repositories.beatmap_cache import BeatmapCacheRepository
from repositories.songs_index import SongsIndexRepository

class ResolveSource(Enum):
    CACHE      = "cache"
    LOCAL_FILE = "local_file"
    REMOTE_API = "remote_api"

@dataclass
class ResolvedBeatmap:
    info: BeatmapInfo
    source: ResolveSource

class BeatmapResolver:
    """
    Single authority for "give me beatmap metadata".
    Fallback order: cache → local .osu header → remote API.
    Writes successful remote/local results back to cache.
    """

    def __init__(
        self,
        cache_repo: BeatmapCacheRepository,
        songs_repo: SongsIndexRepository | None,  # None when songs_path not configured
        api: OssapiAsync,
    ) -> None: ...

    @classmethod
    def from_environment(cls) -> 'BeatmapResolver':
        """
        Wiring factory:
          1. Read ServerSettings.
          2. If osu_songs_path_override exists, use it.
          3. Else use OsuClientDiscovery.discover_songs_path().
          4. Build SongsIndexRepository only when a valid path is found.
        """
        ...

    async def resolve(
        self,
        md5: str | None = None,
        beatmap_id: int | None = None,
    ) -> ResolvedBeatmap | None:
        """
        Tries each source in order, returns first non-None result.
        On remote success, calls _write_to_cache().
        """
        ...

    def _from_cache(
        self,
        md5: str | None,
        beatmap_id: int | None,
    ) -> BeatmapInfo | None: ...

    def _from_local(
        self,
        md5: str | None,
        beatmap_id: int | None,
    ) -> BeatmapInfo | None:
        """
        Delegates to SongsIndexRepository, parses header,
        constructs BeatmapInfo. ranked_status defaults to PENDING
        when read from local file (no API to confirm rank).
        """
        ...

    async def _from_api(
        self,
        md5: str | None,
        beatmap_id: int | None,
    ) -> BeatmapInfo | None:
        """Calls OssapiAsync.beatmap(), maps response to BeatmapInfo."""
        ...

    def _write_to_cache(self, info: BeatmapInfo) -> None: ...

    @staticmethod
    def _from_ossapi_beatmap(beatmap) -> BeatmapInfo:
        """ossapi.Beatmap → BeatmapInfo. Used by _from_api."""
        ...
```

**Why a `ResolvedBeatmap` wrapper:** Knowing the source lets you surface a small
indicator in the GUI or logs ("loaded from cache / local / API") and makes it easier
to reason about cache staleness later.

---

## 12. `usecases/score_sync.py` (NEW)

```python
from osuProtocol.client_web import (
    Score, LazerScore, LegacyScore,
    Scores, LeaderboardScore, ScoringAlgorithm,
)

class ScoreSyncPolicy:
    """
    Pure functions — no I/O, no state.
    This is the single source of truth for how stable and lazer scores are unified.
    """

    @staticmethod
    def identity_key(score: Score) -> str:
        """
        Returns a string that identifies "same player, same mod set" across
        stable and lazer representations.
        Format: "{user_id}:{canonical_mod_bits}"
        canonical_mod_bits normalises LazerScore.enabled_mods (list[str])
        down to osuMods int the same way _mods_from_v2_score does.
        This replaces the username-keyed dedup in Scores.remove_duplicates().
        """
        ...

    @staticmethod
    def resolve_conflict(
        a: Score,
        b: Score,
        algorithm: ScoringAlgorithm,
    ) -> Score:
        """
        Given two scores with the same identity_key, return the one that
        ranks higher under `algorithm`.
        PP mode  → compare score.pp
        LAZER mode → compare effective lazer score
            (LegacyScore uses .lazer_score(), LazerScore uses .total_score)
        """
        ...

    @staticmethod
    def merge_and_rank(
        lazer_scores: Scores | None,
        stable_scores: Scores | None,
        algorithm: ScoringAlgorithm,
        limit: int,
    ) -> list[LeaderboardScore]:
        """
        Full pipeline in one call:
          1. Combine both lists into a single Scores.
          2. Dedupe by identity_key using resolve_conflict.
          3. Sort by algorithm.
          4. Slice to limit.
          5. Convert each Score → LeaderboardScore (with 1-based position).
        Returns an empty list if both inputs are None/empty.

        This replaces the scattered:
            scores.remove_duplicates()
            scores.set_scoring_algorithm(...)
            scores.sort_by_algorithm()
            scores = scores[:score_limit]
            for index, score in enumerate(scores): LeaderboardScore.from_score(...)
        in controllers/subdomains/osu.py.
        """
        ...
```

---

## 13. `usecases/leaderboards.py` (NEW)

```python
from dataclasses import dataclass
from ossapi import OssapiAsync, OssapiV1
import asyncio

from models.database.profiles import ProfileData
from models.beatmap_cache import BeatmapInfo
from osuProtocol.server_packets import osuGameMode, osuMods
from osuProtocol.client_web import (
    LeaderboardType, Leaderboard, LeaderboardHeader,
    GraveyardLeaderboard, osuMapStatus, ScoringAlgorithm,
)
from usecases.beatmap_resolver import BeatmapResolver, ResolvedBeatmap
from usecases.providers.lazer_scores import LazerScoreProvider
from usecases.providers.stable_scores import StableScoreProvider
from usecases.score_sync import ScoreSyncPolicy

@dataclass
class LeaderboardRequest:
    """All inputs the controller has parsed from the HTTP query string."""
    profile_data: ProfileData
    game_mode: osuGameMode
    leaderboard_type: LeaderboardType
    mods: osuMods
    beatmap_md5: str
    map_set_id: int     # the `i` query param — NOT necessarily a beatmap ID

class LeaderboardService:
    """
    Single orchestration entry-point for leaderboard requests.
    Construct once per request — it holds no shared mutable state.
    """

    def __init__(
        self,
        resolver: BeatmapResolver,
        lazer_provider: LazerScoreProvider,
        stable_provider: StableScoreProvider,
    ) -> None: ...

    async def build(self, request: LeaderboardRequest) -> bytes:
        """
        1. resolver.resolve(md5, id) → ResolvedBeatmap | None
           └─ None → return GraveyardLeaderboard().serialize()
        2. asyncio.gather(
               lazer_provider.fetch(...),
               stable_provider.fetch(...)
           )
        3. ScoreSyncPolicy.merge_and_rank(...) → list[LeaderboardScore]
        4. Build LeaderboardHeader + Leaderboard, return .serialize()
        """
        ...

    @staticmethod
    def _build_header(
        beatmap: BeatmapInfo,
        num_scores: int,
    ) -> LeaderboardHeader: ...

    @staticmethod
    def _make_service(profile_data: ProfileData) -> 'LeaderboardService':
        """
        Factory that wires together resolver + providers from profile/settings.
        Call this from the controller so it doesn't know about construction details.
        Usage: service = LeaderboardService._make_service(profile_data)
        """
        ...
```

---

## 14. `usecases/beatmaps.py` (MODIFY)

Replace the existing `get_beatmap` and `get_beatmap_set` functions.  
All existing callers (bancho.py, osu.py) should continue to work — just the
internals change.

```python
# KEEP existing ApiV2CredentialsError class for backward compat.

async def get_beatmap(
    beatmap_md5: str | None = None,
    beatmap_id: int | None = None,
) -> BeatmapInfo | None:
    """
    Delegates to BeatmapResolver.resolve().
    Raises ApiV2CredentialsError if remote API is needed but credentials missing.
    Drop-in replacement for the current sync get_beatmap().
    """
    ...

async def get_beatmapset_title_artist(
    beatmap: BeatmapInfo,
) -> tuple[str, str]:
    """
    Returns (artist_unicode, title_unicode).
    These now live directly on BeatmapInfo so this is a trivial accessor.
    Replaces the separate get_beatmap_set() call in osu.py that currently
    requires a second API round-trip just to get the artist/title for the header.
    """
    ...
```

**Important note on the second API call:** Currently `osu.py` calls both
`get_beatmap()` and `get_beatmap_set()` independently. Because `BeatmapInfo` carries
`artist_unicode` and `title_unicode` directly (populated from the .osu header or from
the API's beatmap response — not from a separate beatmapset request), the second call
disappears entirely. That alone saves one network round-trip per leaderboard load.

---

## 15. `controllers/subdomains/osu.py` (MODIFY — `get_leaderboard` only)

After the refactor this endpoint becomes parse-and-serialize only:

```python
@osu.get('/web/osu-osz2-getscores.php')
async def get_leaderboard(
    # ... same Query params as today ...
) -> Response:
    session = usecases.sessions.get_current_session()
    if session is None or session["profile_name"] is None:
        return NULL_RESPONSE

    profile = usecases.profiles.get_profile(session["profile_name"])
    if profile is None:
        return NULL_RESPONSE

    profile_data = profile[session["profile_name"]]

    request = LeaderboardRequest(
        profile_data=profile_data,
        game_mode=osuGameMode(mode_arg),
        leaderboard_type=LeaderboardType(leaderboard_type),
        mods=osuMods(mods_arg),
        beatmap_md5=map_md5,
        map_set_id=map_set_id,
    )

    service = LeaderboardService._make_service(profile_data)
    result: bytes = await service.build(request)

    return Response(content=result)
```

Everything between the profile lookup and the `Response(...)` that currently lives in
this handler — beatmap fetch, score fetch, dedupe, sort, header build, serialize —
moves into `LeaderboardService.build()` and the classes it calls.

---

## Migration Order (do these in sequence to keep the app running)

1. **Add `models/beatmap_cache.py`** — pure TypedDict, no deps.
2. **Add `models/osu_client.py`** + **`usecases/osu_client_discovery.py`** (signatures only).
3. **Add `osu_songs_path_override` to `ServerSettings`** + GUI setting (optional fallback only).
4. **Add `BEATMAP_CACHE_FILE` to constants.**
5. **Add `repositories/beatmap_cache.py`** — no callers yet, safe to add.
6. **Add `repositories/songs_index.py`** — no callers yet, safe to add.
7. **Add `usecases/providers/__init__.py`** — move `get_ossapi_async` + `get_ossapi_v1` here; update usecases/scores.py and usecases/beatmaps.py to import from here.
8. **Add `usecases/providers/lazer_scores.py`** — migrate normalization logic from scores.py.
9. **Add `usecases/providers/stable_scores.py`** — migrate normalization logic from scores.py. Wrap in `asyncio.to_thread`.
10. **Add `usecases/beatmap_resolver.py`** — wire up cache + songs + async API + discovery fallback.
11. **Update `usecases/beatmaps.py`** — `get_beatmap` delegates to resolver. Change return type to `BeatmapInfo`.
12. **Fix callers of `get_beatmap`** (`bancho.py`, `osu.py`) to expect `BeatmapInfo` — field names are the same so the only real change is `await`.
13. **Add `usecases/score_sync.py`** — pure logic, no I/O, easy to test standalone.
14. **Add `usecases/leaderboards.py`** — wire everything together.
15. **Slim down `controllers/subdomains/osu.py`** — swap old body for `LeaderboardService._make_service(...)`.
16. **Delete dead code** in `usecases/scores.py` — `get_scores_for_beatmap_id`, `get_scores_for_beatmap_md5`, `get_legacy_scores_for_beatmap_id`, `get_legacy_scores_for_beatmap_md5`, and both `get_ossapi` copies.
