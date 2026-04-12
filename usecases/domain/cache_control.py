"""
Domain-specific cache decorators and control functions.

Usage:
    @cache_leaderboard
    async def get_leaderboard():
        pass

    # Clear leaderboard cache
    clear_leaderboard_cache()
"""

from datetime import timedelta
from typing import Callable, TypeVar, cast

from usecases.adapters.cache import cache_group, clear_domain

F = TypeVar("F", bound=Callable)


# ============================================================================
# Cache Decorators by Domain
# ============================================================================


def cache_leaderboard(func: F) -> F:
    """Cache decorator for leaderboard-related functions (30 min default)."""
    return cast(F, cache_group("leaderboard", ttl=timedelta(minutes=30))(func))


def cache_scores(func: F) -> F:
    """Cache decorator for score-related functions (30 min default)."""
    return cast(F, cache_group("scores", ttl=timedelta(minutes=30))(func))


def cache_beatmaps(func: F) -> F:
    """Cache decorator for beatmap-related functions (1 hour default)."""
    return cast(F, cache_group("beatmaps", ttl=timedelta(hours=1))(func))


def cache_profiles(func: F) -> F:
    """Cache decorator for profile-related functions (30 min default)."""
    return cast(F, cache_group("profiles", ttl=timedelta(minutes=30))(func))


def cache_achievements(func: F) -> F:
    """Cache decorator for achievement-related functions (1 hour default)."""
    return cast(F, cache_group("achievements", ttl=timedelta(hours=1))(func))


def cache_replays(func: F) -> F:
    """Cache decorator for replay-related functions (1 hour default)."""
    return cast(F, cache_group("replays", ttl=timedelta(hours=1))(func))


def cache_direct(func: F) -> F:
    """Cache decorator for direct search functions (30 min default)."""
    return cast(F, cache_group("direct", ttl=timedelta(minutes=30))(func))


def cache_chats(func: F) -> F:
    """Cache decorator for chat-related functions (5 min default)."""
    return cast(F, cache_group("chats", ttl=timedelta(minutes=5))(func))


def cache_avatars(func: F) -> F:
    """Cache decorator for avatar-related functions (forever)."""
    return cast(F, cache_group("avatars", ttl="forever")(func))


# ============================================================================
# Cache Clearing Functions
# ============================================================================


def clear_leaderboard_cache() -> int:
    """Clear all leaderboard caches."""
    count = clear_domain("leaderboard")
    print(f"Cleared {count} leaderboard cache(s)")
    return count


def clear_scores_cache() -> int:
    """Clear all score caches."""
    count = clear_domain("scores")
    print(f"Cleared {count} score cache(s)")
    return count


def clear_beatmaps_cache() -> int:
    """Clear all beatmap caches."""
    count = clear_domain("beatmaps")
    print(f"Cleared {count} beatmap cache(s)")
    return count


def clear_profiles_cache() -> int:
    """Clear all profile caches."""
    count = clear_domain("profiles")
    print(f"Cleared {count} profile cache(s)")
    return count


def clear_achievements_cache() -> int:
    """Clear all achievement caches."""
    count = clear_domain("achievements")
    print(f"Cleared {count} achievement cache(s)")
    return count


def clear_replays_cache() -> int:
    """Clear all replay caches."""
    count = clear_domain("replays")
    print(f"Cleared {count} replay cache(s)")
    return count


def clear_direct_cache() -> int:
    """Clear all direct search caches."""
    count = clear_domain("direct")
    print(f"Cleared {count} direct cache(s)")
    return count


def clear_chats_cache() -> int:
    """Clear all chat caches."""
    count = clear_domain("chats")
    print(f"Cleared {count} chat cache(s)")
    return count


def clear_avatars_cache() -> int:
    """Clear all avatar caches."""
    count = clear_domain("avatars")
    print(f"Cleared {count} avatar cache(s)")
    return count


# ============================================================================
# Batch Clearing
# ============================================================================


def clear_all_domain_caches() -> int:
    """Clear all domain-specific caches. Returns total count cleared."""
    domains = [
        "leaderboard",
        "scores",
        "beatmaps",
        "profiles",
        "achievements",
        "replays",
        "direct",
        "chats",
        "avatars",
    ]
    total = 0
    for domain in domains:
        total += clear_domain(domain)
    print(f"Cleared all domain caches ({total} total)")
    return total
