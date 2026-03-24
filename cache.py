import functools
import inspect
from datetime import datetime, timedelta
from typing import Any, Callable, Generic, TypeVar, cast

from adapters import log

KEY = TypeVar("KEY")
VALUE = TypeVar("VALUE")
F = TypeVar("F", bound=Callable[..., Any])


class Cache(Generic[KEY, VALUE]):
    def __init__(self, time_to_live: timedelta):
        self.time_to_live = time_to_live
        self.store: dict[KEY, tuple[VALUE, datetime]] = {}

    def get(self, key: KEY) -> VALUE | None:
        if key not in self.store:
            return None

        value, time_set = self.store[key]
        current_time = datetime.now()
        if current_time - time_set > self.time_to_live:
            del self.store[key]
            return None

        return value

    def set(self, key: KEY, value: VALUE) -> None:
        self.store[key] = (value, datetime.now())
        log.success(f"Cached value for key: {key}")

    def clear(self) -> None:
        self.store.clear()
        log.success("Cache cleared")

    def remove(self, key: KEY) -> None:
        if key in self.store:
            del self.store[key]
            log.success(f"Removed key from cache: {key}")


def _make_hashable(obj: Any) -> Any:
    """Convert unhashable types to hashable equivalents for cache keys."""
    try:
        # Try to hash directly (fastest path)
        hash(obj)
        return obj
    except TypeError:
        # Unhashable type; convert to hashable representation
        if isinstance(obj, dict):
            return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, (list, tuple)):
            return tuple(_make_hashable(item) for item in obj)
        else:
            # For Pydantic models and custom objects, use their id
            return id(obj)


class CacheFunction(Cache[Any, F]):
    def function(self, func: F) -> F:

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):  # type: ignore

                # Create a hashable key from args and kwargs
                hashable_args = tuple(_make_hashable(arg) for arg in args)
                hashable_kwargs = tuple(
                    sorted((k, _make_hashable(v)) for k, v in kwargs.items())
                )
                cache_key = (hashable_args, hashable_kwargs)

                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                result = await func(*args, **kwargs)
                self.set(
                    cache_key, result
                )  # Cache the function result for future calls
                return result
        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):  # type: ignore
                # Create a hashable key from args and kwargs
                hashable_args = tuple(_make_hashable(arg) for arg in args)
                hashable_kwargs = tuple(
                    sorted((k, _make_hashable(v)) for k, v in kwargs.items())
                )
                cache_key = (hashable_args, hashable_kwargs)

                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                result = func(*args, **kwargs)
                self.set(
                    cache_key, result
                )  # Cache the function result for future calls
                return result

        return cast(F, wrapper)


from pathlib import Path

from models.bancho.scores import Score, Scores
from models.database.beatmaps import CurrentBeatmap as Beatmap

MD5 = str
SET_ID = int
FILE_NAME = str
beatmap = Cache[MD5, Beatmap](time_to_live=timedelta(minutes=30))
osu_file_path_by_md5 = Cache[MD5, Path](time_to_live=timedelta(minutes=30))
osu_files_by_set_id_and_filename = Cache[tuple[SET_ID, FILE_NAME], Path](
    time_to_live=timedelta(minutes=30)
)
osu_file_path_by_beatmap_id_and_set_id = Cache[tuple[int, int], Path](
    time_to_live=timedelta(minutes=30)
)
beatmap_by_md5 = Cache[MD5, Beatmap](time_to_live=timedelta(minutes=30))
osu_file_path_by_file_name = Cache[FILE_NAME, Path](time_to_live=timedelta(minutes=30))
beatmap_by_id = Cache[int, Beatmap](time_to_live=timedelta(minutes=30))
osu_file_path_by_set_id_and_md5 = Cache[tuple[SET_ID, MD5], Path](
    time_to_live=timedelta(minutes=30)
)
score_for_user_on_beatmap_by_md5 = Cache[MD5, Score](time_to_live=timedelta(minutes=5))
friends_scores_for_beatmap_by_md5 = Cache[MD5, Scores](
    time_to_live=timedelta(minutes=5)
)
get_any_scores_for = CacheFunction(time_to_live=timedelta(minutes=10))
get_mod_specific_scores_for = CacheFunction(time_to_live=timedelta(minutes=10))
get_replay = CacheFunction(time_to_live=timedelta(minutes=30))
get_scores_for = CacheFunction(time_to_live=timedelta(minutes=10))
get_friends_scores_for_beatmap = CacheFunction(time_to_live=timedelta(minutes=10))
get_score_for_user_on_beatmap = CacheFunction(time_to_live=timedelta(minutes=5))
rank_for_pp = CacheFunction(time_to_live=timedelta(minutes=60))
position_for_score = CacheFunction(time_to_live=timedelta(minutes=60))
get_replay_frames_for_score_id = CacheFunction(time_to_live=timedelta(minutes=60))
