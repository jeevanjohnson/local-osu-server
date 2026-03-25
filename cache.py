import functools
import inspect
from datetime import datetime, timedelta
from typing import Any, Callable, Generic, Literal, TypeVar, cast

from adapters import log

KEY = TypeVar("KEY")
VALUE = TypeVar("VALUE")
F = TypeVar("F", bound=Callable[..., Any])


class Cache(Generic[KEY, VALUE]):
    """A simple in-memory cache with time-based expiration."""

    def __init__(
        self, time_to_live: timedelta | Literal["forever"], save_on_none: bool = True
    ) -> None:
        self.time_to_live = time_to_live
        self.save_on_none = save_on_none
        self.store: dict[KEY, tuple[VALUE, datetime]] = {}

    @property
    def size(self) -> int:
        return len(self.store)

    def get(self, key: KEY) -> VALUE | None:
        if key not in self.store:
            return None

        value, time_set = self.store[key]
        current_time = datetime.now()
        if self.time_to_live != "forever":
            if (current_time - time_set) > self.time_to_live:  # type: ignore
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

def _format_timedelta(delta: timedelta) -> str:
    total_seconds = delta.total_seconds()
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{int(minutes)} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    return f"{int(hours)} hour{'s' if hours != 1 else ''}"

class CacheFunction(Cache[Any, F]):
    """A decorator class that caches the results of function calls based on their arguments."""

    def function(self, func: F) -> F:
        try:
            is_method = list(inspect.signature(func).parameters)[0] in ("self", "cls")
        except IndexError:
            is_method = False

        if self.time_to_live == "forever":
            ttl_desc = "forever"
        else:
            ttl_desc = _format_timedelta(self.time_to_live) # type: ignore

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):  # type: ignore
                # Keep original args for calling the function, use stripped args for cache key
                cache_args = args[1:] if is_method else args

                # Create a hashable key from args and kwargs
                hashable_args = tuple(_make_hashable(arg) for arg in cache_args)
                hashable_kwargs = tuple(
                    sorted((k, _make_hashable(v)) for k, v in kwargs.items())
                )
                cache_key = (hashable_args, hashable_kwargs)

                cached = self.get(cache_key)
                if not self.save_on_none or cached is not None:
                    return cached

                result = await func(*args, **kwargs)
                self.set(
                    cache_key, result
                )  # Cache the function result for future calls
                return result
        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):  # type: ignore
                # Keep original args for calling the function, use stripped args for cache key
                cache_args = args[1:] if is_method else args
                # Create a hashable key from args and kwargs
                hashable_args = tuple(_make_hashable(arg) for arg in cache_args)
                hashable_kwargs = tuple(
                    sorted((k, _make_hashable(v)) for k, v in kwargs.items())
                )
                cache_key = (hashable_args, hashable_kwargs)

                cached = self.get(cache_key)
                if not self.save_on_none or cached is not None:
                    return cached

                result = func(*args, **kwargs)
                self.set(
                    cache_key, result
                )  # Cache the function result for future calls
                return result

        original_doc = func.__doc__ or ""
        note = f"\n\nNote: Results are cached for {ttl_desc}."
        wrapper.__doc__ = original_doc + note

        return cast(F, wrapper)

def cached(
    time_to_live: timedelta | Literal["forever"] = timedelta(minutes=10),
    save_on_none: bool = True,
) -> Callable[[F], F]:
    return CacheFunction(time_to_live=time_to_live, save_on_none=save_on_none).function

def cached_for_one_minute(func: F) -> F:
    return CacheFunction(time_to_live=timedelta(minutes=1)).function(func)

def cached_for_five_minutes(func: F) -> F:
    return CacheFunction(time_to_live=timedelta(minutes=5)).function(func)

def cached_for_10_minutes(func: F) -> F:
    return CacheFunction(time_to_live=timedelta(minutes=10)).function(func)

def cached_for_30_minutes(func: F) -> F:
    return CacheFunction(time_to_live=timedelta(minutes=30)).function(func)

def cached_for_one_hour(func: F) -> F:
    return CacheFunction(time_to_live=timedelta(hours=1)).function(func)

def cached_forever(func: F) -> F:
    return CacheFunction(time_to_live="forever").function(func)
