import functools
import inspect
from datetime import datetime, timedelta
from typing import Any, Callable, Generic, Literal, TypeVar, cast

# from adapters import log

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
        print(f"Cached value for key: {key}")

    def clear(self) -> None:
        self.store.clear()
        print("Cache cleared")

    def remove(self, key: KEY) -> None:
        if key in self.store:
            del self.store[key]
            print(f"Removed key from cache: {key}")


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


class CacheManager:
    """Manages all cached functions globally for easy cache control."""

    def __init__(self):
        self.caches: dict[str, Cache[Any, Any]] = {}
        self.domains: dict[str, list[str]] = {}

    def register(
        self, func_name: str, cache: Cache[Any, Any], domain: str | None = None
    ) -> None:
        """Register a cache instance for a function, optionally under a domain."""
        self.caches[func_name] = cache
        if domain:
            if domain not in self.domains:
                self.domains[domain] = []
            self.domains[domain].append(func_name)
            print(f"Registered cache for function: {func_name} (domain: {domain})")
        else:
            print(f"Registered cache for function: {func_name}")

    def clear_cache(self, func_name: str) -> bool:
        """Clear cache for a specific function. Returns True if found and cleared."""
        if func_name in self.caches:
            self.caches[func_name].clear()
            return True
        return False

    def clear_domain(self, domain: str) -> int:
        """Clear all caches in a domain. Returns count cleared."""
        if domain not in self.domains:
            return 0
        cleared = 0
        for func_name in self.domains[domain]:
            if func_name in self.caches:
                self.caches[func_name].clear()
                cleared += 1
        return cleared

    def clear_cache_pattern(self, pattern: str) -> int:
        """Clear all caches matching a pattern (e.g., 'bancho*'). Returns count cleared."""
        import fnmatch

        cleared = 0
        for func_name in list(self.caches.keys()):
            if fnmatch.fnmatch(func_name, pattern):
                self.caches[func_name].clear()
                cleared += 1
        return cleared

    def clear_all(self) -> int:
        """Clear all caches. Returns count cleared."""
        count = len(self.caches)
        for cache in self.caches.values():
            cache.clear()
        return count

    def list_caches(self) -> dict[str, int]:
        """List all registered caches and their sizes."""
        return {name: cache.size for name, cache in self.caches.items()}


# Global cache manager instance
_cache_manager = CacheManager()


class CacheFunction(Cache[Any, F]):
    """A decorator class that caches the results of function calls based on their arguments."""

    def function(self, func: F, domain: str | None = None) -> F:
        try:
            is_method = list(inspect.signature(func).parameters)[0] in ("self", "cls")
        except IndexError:
            is_method = False

        if self.time_to_live == "forever":
            ttl_desc = "forever"
        else:
            ttl_desc = _format_timedelta(self.time_to_live)  # type: ignore

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

        # Attach cache instance to wrapper for external access
        wrapper.__cache__ = self  # type: ignore
        wrapper.__cache_function_name__ = func.__qualname__  # type: ignore

        # Register this cache globally
        _cache_manager.register(func.__qualname__, self, domain)

        return cast(F, wrapper)


def cached(
    time_to_live: timedelta | Literal["forever"] = timedelta(minutes=10),
    save_on_none: bool = True,
) -> Callable[[F], F]:
    return CacheFunction(time_to_live=time_to_live, save_on_none=save_on_none).function


def cache_group(
    domain: str, ttl: timedelta | Literal["forever"] = timedelta(minutes=10)
) -> Callable[[F], F]:
    """Create a cache decorator for a specific domain with optional TTL override."""

    def decorator(func: F) -> F:
        cache = CacheFunction(time_to_live=ttl)
        return cache.function(func, domain=domain)

    return decorator


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


# ============================================================================
# Public Cache Control API
# ============================================================================


def clear_cache(func_name: str) -> bool:
    """
    Clear cache for a specific function by name.

    Example: clear_cache("usecases.bancho_scores.get_scores_for")
    Returns True if cache was found and cleared, False otherwise.
    """
    return _cache_manager.clear_cache(func_name)


def clear_domain(domain: str) -> int:
    """
    Clear all caches in a specific domain.

    Example: clear_domain("leaderboard")
    Returns count of caches cleared.
    """
    return _cache_manager.clear_domain(domain)


def clear_cache_pattern(pattern: str) -> int:
    """
    Clear all caches matching a glob pattern.

    Examples:
    - clear_cache_pattern("*bancho*") - clears all caches with 'bancho' in name
    - clear_cache_pattern("usecases.bancho_*") - clears all bancho_* functions
    - clear_cache_pattern("*") - clears everything

    Returns count of caches cleared.
    """
    return _cache_manager.clear_cache_pattern(pattern)


def clear_all_caches() -> int:
    """Clear all caches completely. Returns count of caches cleared."""
    return _cache_manager.clear_all()


def get_cache_stats() -> dict[str, int]:
    """Get all registered caches and their current sizes."""
    return _cache_manager.list_caches()
