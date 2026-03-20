# Purpose

This directory contains personal notes I have taken while working on this project.

# 3.20.2026

- MODS STABLE -> LAZER CONVERSION (int -> list[str])
- WORK ON LB REWORK
- FIND THE DIFFERENCE BETWEEN SCOREV2 & LAZER SCORING TO ENSURE ACCURATE LEADERBOARD SYNCING
- For trying to watch replays from lazer, we'll manually download to the user's system and ask them to open it in osu! lazer themselves
- Either hardcode settings or figure out how to doctype them in pydantic model
- use more custom error cases
- make log library 
- - bypass errors, save errors, use pydantic model to save
- - decorator on top of funcs to save time 
- - timestamp, func name, error type, error message, traceback, and other relevant info like states of objects when error happened
- - can ask to log and save but not crash, or log and save and crash, or just log and save
- map updates (when md5s don't match but ids do)
- convert db mods from stable format to lazer format (list[str])
- forget about katu & geki count saving since lazer doesn't use them anymore
- scoring algorithm probably a calculator folder of all calculators, example: calculator/pp.py, calculator/score.py, calculator/fundamentals.py, calculator/prediction.py
- btw for prediction.py we don't need to scan all 10k users we can just get a couple from a wide range and then map the line of best fit

# 3.17.2026

You want a concrete architecture plan before coding, focused on 3 pain points: stable+lazer score sync, async leaderboard loading, and beatmap lookup fallbacks. I’ll quickly inspect the current flow in your score/usecase/repository layers so the recommendations are specific to your codebase, then I’ll give you a proposed architecture and migration path.

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/usecases/scores.py#1-1), lines 1 to 260

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/usecases/beatmaps.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/repositories/resources.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/repositories/profiles.py)

I found the core issue areas already: score fetching and beatmap fetching are duplicated and tightly coupled to live API clients, which makes syncing logic hard to evolve. Next I’m checking request-entry and score model files to map where to introduce clean boundaries without breaking current behavior.

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/osuProtocol/client_web.py#1-1), lines 1 to 360

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/usecases/bancho.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/controllers/subdomains/bancho.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/repositories/sessions.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/osuProtocol/client_web.py#360-360), lines 360 to 380

I’ve confirmed your score model already contains merge/sort behavior, but request orchestration still looks coupled. I’m now tracing the exact leaderboard request path to identify where sync logic, async fetch, and cache fallback should live.

Searched for regex `get_scores_for_beatmap_md5|get_scores_for_beatmap_id|get_legacy_scores_for_beatmap_id|remove_duplicates|sort_by_algorithm` (`**/*.py`), 10 results

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/controllers/subdomains/osu.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/controllers/subdomains/beatmaps.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/main.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/usecases/scores.py#260-260), lines 260 to 469

Searched for regex `beatmap_cache|songs folder|glob|pathlib|osu file|checksum` (`**/*.py`), 20 results

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/constants.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/models/database/server_settings.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/repositories/server_settings.py)

Read [](file:///c%3A/Users/jeeva/Desktop/LOS2026/database/jsonfile.py)

Searched for regex `def get_leaderboard|scores.remove_duplicates|scores.sort_by_algorithm|def get_scores_for_beatmap\(|def _get_scores_for_beatmap\(|def get_scores_for_beatmap_id\(|def get_scores_for_beatmap_md5\(|def get_ossapi\(|def get_beatmap\(|class JsonFile|async def __aenter__|def __enter__` (`**/*.py`), 15 results

I have enough context to give you a concrete target architecture and a migration sequence tailored to your current files. Next I’ll break down: what is currently causing the mess, the architecture to replace it, and a step-by-step implementation order that keeps the app working while you refactor.

Created 4 todos

Completed: *Design async and cache architecture* (3/4)

Your instinct is right: the feature is hard mainly because responsibilities are mixed, not because the logic itself is impossible.

**Why It Feels Messy Today**
1. The leaderboard endpoint is doing orchestration, policy, and formatting all at once in osu.py.  
2. Stable and lazer fetch paths are duplicated in two nearly identical functions in scores.py and scores.py.  
3. API client construction is duplicated too, in both scores.py and beatmaps.py, so auth/retry/caching concerns are scattered.  
4. Sync policy is implicit and late: merge first, then dedupe/sort in endpoint flow (scores.py, osu.py).  
5. The endpoint is async but most work is blocking sync I/O, so it can still stall under load (osu.py).  
6. You already have async primitives in your JSON layer, but normal usage uses sync enter/exit, so lock strategy is inconsistent (jsonfile.py, jsonfile.py).  
7. Beatmap lookup currently goes straight to API paths; local-first lookup chain is not modeled as a first-class service yet (beatmaps.py).

That is why implementation feels brittle: no single place defines “how scores are unified” or “how beatmaps are resolved.”

**Target Architecture (No Code Yet)**
1. Add a Leaderboard Application Service as the single orchestrator.
2. Split data sources into providers:
- LazerScoreProvider
- StableScoreProvider
- BeatmapProvider chain
3. Normalize into one internal score model before any dedupe/sort.
4. Move merge rules into a ScoreSyncPolicy service.
5. Make all external I/O async behind provider interfaces.
6. Keep controller thin: parse request -> call service -> serialize response.

**The Most Important New Piece: Score Sync Policy**
Define one authoritative policy module for:
1. Identity key for “same play” vs “same player best”.
2. Conflict resolution: when stable and lazer versions overlap, pick by configured scoring algorithm.
3. Ranking metric selection (score/pp) in one place, not in endpoint.
4. Provenance tracking (source=stable/lazer) for debugging and UI labels.

This removes hidden behavior from route handlers and makes syncing predictable.

**Beatmap Resolution Pipeline You Asked For**
Create BeatmapResolver with strict fallback order:
1. Check beatmap_cache.json repository (persistent cache).
2. If missing, check local Songs folder index using pathlib + glob.
3. Parse found .osu and map to beatmap DTO.
4. If still missing, call remote API.
5. Write successful result back to cache for future hits.

Also add:
1. Memory cache (TTL) above JSON cache for hot lookups.
2. Background index refresh for Songs folder so requests do not rescan disk every time.
3. Negative-cache entries for short TTL when remote miss occurs.

**Async Plan (Without Big-Bang Rewrite)**
1. Keep your current logic, but wrap blocking ossapi calls in transitional async adapters using thread offload.
2. Introduce shared request-scoped clients/session objects in providers.
3. Use gather for independent calls:
- stable scores
- lazer scores
- beatmap metadata (if needed)
4. Add timeout + retry policy only in provider layer, never in controller.

This gives immediate latency wins while preserving behavior.

**Recommended Project Shape**
Within your current style (usecases/repositories), add:
1. usecases/leaderboards.py as orchestration entrypoint.
2. usecases/score_sync.py for merge/dedupe/ranking policy.
3. repositories/beatmap_cache.py for beatmap_cache.json access.
4. repositories/songs_index.py for local Songs scanning/index reads.
5. usecases/beatmap_resolver.py for fallback chain.
6. usecases/providers/ for stable/lazer/remote provider adapters.

**Phased Migration Order**
1. Extract pure merge/dedupe/rank policy from endpoint flow first.
2. Replace duplicated score fetch functions with one parameterized provider flow.
3. Introduce BeatmapResolver chain (cache -> songs -> api).
4. Convert orchestration service to async, keep internals transitional where needed.
5. Slim down endpoint to only request/response mapping.
6. Add tests around policy and resolver order before performance tuning.

**Why This Is Better Than Current**
1. One place to reason about score unification.
2. One place to reason about beatmap fallback order.
3. Async concurrency where it matters, without scattering async complexity everywhere.
4. Cleaner future changes: adding another source or scoring mode becomes provider/policy work, not route surgery.

If you want, next step can be a concrete blueprint document (interfaces, DTOs, and method signatures only) mapped to your exact files so implementation is almost mechanical.

# 3.16.2026
- ~~Fix GUI now since we know when the client is opened or not~~
- Begin tackling leaderboards and score_submission
- - Support lazer scores being seen on lbs but nots its replys
- - Have personal tags `[rxonly] cover` and then server tags `cover (1.2x Rate)`, server tags can allow us for when we rate change on a map we can see the og leaderboard map and everyone's rate but now we can see our rate in terms of speed and do score multiplying accordingly
- GUI profile specific settings
- rank button click for gui
- recently loaded score on gui
- when storing scores, store the osu file in case if stuff gets lost, we can still figure out a way to load replay

## 3.15.2026

`field(init=False)` excludes the field from being included in the generated `__init__` method of a dataclass.

`IntFlag` allows multiple members to be combined using the OR bitwise operation `|`. This is useful for representing a combination of options or flags. 

`|=` regarding binary operations is the bitwise OR operator. It compares each bit position and keeps a 1 if either of the bits is 1. For example, if you have the binary numbers 1101 and 1011, the bitwise OR would be 1111 because at least one of the bits in each position is 1. In context of uleb128, when we set the most significant bit to 1, so we use this operator to set that bit to 1 while keeping the other bits unchanged.

`&` regarding binary operations is the bitwise AND operator. It compares each bit position and only keeps a 1 where both bits are 1. For example, if you have the binary numbers 1101 and 1011, the bitwise AND would be 1001 because only the first and last bits are both 1. In context of uleb

For writing uleb128:
- You are given a number that you want to encode as uleb128.
```
While number > 0:
    Take the 7 least significant bits of the number.
        Ex. 12345678, the 7 least significant bits of this are 8,7,6,5,4,3,2,1.
    Check if the most significant bit (the first bit) is = 1.

    If equals 1:
        This means there are more bytes to read, so we set the most significant bit to 1 and write this byte to the output.
    If equals 0:
        This means this is the last byte and we are done encoding.
```

`int 32` is just an int that is 4 bytes long. It can represent values from -2,147,483,648 to 2,147,483,647. 

`int 64` is an int that is 8 bytes long. It can represent values from -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807.

`unsigned int` can't hold negative values. While a `signed int` can.

`bytes(size: int)` creates a byte object of the specified size filled with null bytes (0x00).

`enum.unique` checks if there are any members sharing the same value. If so, an error is raised.

osu! Packet writing Protocol (little endian):
- Packet ID (unsigned short, 2 bytes)
- Packet Length (padding, 1 byte)
- Packet Data Length (unsigned int, 4 bytes)
- Packet Data (variable length)

Endian refers to the order of bytes in a data type (like ints or floats). For little-endian, the least significant byte is stored first. The "least significant byte" is the byte that represents the smallest part of the number. For example, 1234, the least significant number is 4. So in terms of bytes, the least significant byte would be the one that represents the 4. In little-endian, this byte would be stored first in memory in little-endian format. Then 3, Then 2, and then 1. So the bytes would be stored in the order of 4, 3, 2, 1.

## 3.14.2026

`multiprocess.Process(..., daemon=bool)` If this is set to `True`, the process will be killed the moment the main process (the script running the processes) exits. If this is set to `False`, the main process will wait for them to finish before exiting.
  
`finally` block act as a cleanup mechanism. You can think about as you try to do something, if an error occurs, you can catch it and handle it, but regardless of whether an error occurs or not, the code in the `finally` block will always execute.

`pip freeze > requirements.txt` to update the dependencies in the `requirements.txt` file.
- Ensure you are in the correct virtual environment before running this command to capture all the necessary dependencies for your project.

`mitmdump -s mitm_script.py` to start the mitmproxy with the specified script.
- This command will run mitmproxy and execute the `mitm_script.py` script,
- `-q` flag is used to suppress the output of mitmproxy, making it "quieter" while running.

`#!/usr/bin/env python` at the top of a Python script is called a shebang line. It tells the operating system how to execute the script.
- `#!/usr/bin/env python` uses the `env` command to find the Python interpreter