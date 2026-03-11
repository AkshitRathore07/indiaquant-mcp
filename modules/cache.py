"""TTL cache wrapper for rate-limited API data."""

from cachetools import TTLCache
import threading

_lock = threading.Lock()

# Separate caches for different data types
_price_cache = TTLCache(maxsize=500, ttl=30)
_history_cache = TTLCache(maxsize=200, ttl=600)
_options_cache = TTLCache(maxsize=100, ttl=300)
_news_cache = TTLCache(maxsize=50, ttl=3600)
_general_cache = TTLCache(maxsize=200, ttl=120)


def get_cached(cache_name: str, key: str):
    """Get a value from the named cache."""
    cache = _get_cache(cache_name)
    with _lock:
        return cache.get(key)


def set_cached(cache_name: str, key: str, value):
    """Set a value in the named cache."""
    cache = _get_cache(cache_name)
    with _lock:
        cache[key] = value


def _get_cache(name: str) -> TTLCache:
    caches = {
        "price": _price_cache,
        "history": _history_cache,
        "options": _options_cache,
        "news": _news_cache,
        "general": _general_cache,
    }
    return caches.get(name, _general_cache)
