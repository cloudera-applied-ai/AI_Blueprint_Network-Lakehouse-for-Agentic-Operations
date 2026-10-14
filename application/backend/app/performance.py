"""Performance utilities for threading and caching"""
import time
import hashlib
import logging
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, Any, Callable, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Thread pool for parallel database queries
_query_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="db_query")


class ResponseCache:
    """Simple in-memory cache with TTL for dashboard responses"""

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    logger.debug(f"Cache hit for {key}")
                    return value
                else:
                    del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: float = 5.0):
        """Set cache value with TTL"""
        with self._lock:
            self._cache[key] = (value, time.time() + ttl_seconds)

    def invalidate(self, key: str):
        """Remove a specific key from cache"""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """Clear all cached values"""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, expiry) in self._cache.items() if now >= expiry]
            for k in expired:
                del self._cache[k]


# Global cache instance
response_cache = ResponseCache()


def cache_response(ttl_seconds: float = 5.0, key_prefix: str = ""):
    """Decorator to cache endpoint responses

    Args:
        ttl_seconds: How long to cache the response (default 5 seconds)
        key_prefix: Prefix for cache key (defaults to function name)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            # Skip 'db' argument as it's not hashable
            cache_args = {k: v for k, v in kwargs.items() if k != 'db'}
            key_data = f"{key_prefix or func.__name__}:{cache_args}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Check cache
            cached = response_cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Returning cached response for {func.__name__}")
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            response_cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


def run_queries_parallel(
    queries: List[Tuple[str, Callable]],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Execute multiple database queries in parallel using thread pool

    Args:
        queries: List of (name, callable) tuples. Each callable should be a
                 function that takes no arguments and returns the query result.
        timeout: Maximum time to wait for all queries (default 30 seconds)

    Returns:
        Dict mapping query names to their results

    Example:
        results = run_queries_parallel([
            ("total_nodes", lambda: db.execute(select(func.count(...))).scalar()),
            ("alert_count", lambda: db.execute(select(func.count(...))).scalar()),
        ])
        total = results["total_nodes"]
        alerts = results["alert_count"]
    """
    results = {}
    futures = {}

    start_time = time.time()

    # Submit all queries to thread pool
    for name, query_func in queries:
        future = _query_executor.submit(query_func)
        futures[future] = name

    # Collect results as they complete
    for future in as_completed(futures, timeout=timeout):
        name = futures[future]
        try:
            results[name] = future.result()
        except Exception as e:
            logger.error(f"Query '{name}' failed: {e}")
            results[name] = None

    elapsed = time.time() - start_time
    logger.debug(f"Parallel queries completed in {elapsed:.3f}s")

    return results


def consolidate_count_query(db, model, group_column, count_column=None):
    """Execute a single GROUP BY query instead of multiple COUNT queries

    Args:
        db: Database session
        model: SQLAlchemy model class
        group_column: Column to group by
        count_column: Column to count (defaults to model.id)

    Returns:
        Dict mapping group values to counts

    Example:
        status_counts = consolidate_count_query(db, FiberNodeModel, FiberNodeModel.status)
        # Returns: {'healthy': 1500, 'degraded': 300, 'outage': 50, 'maintenance': 150}
    """
    from sqlalchemy import select, func

    if count_column is None:
        count_column = model.id

    query = select(
        group_column,
        func.count(count_column)
    ).group_by(group_column)

    result = db.execute(query).fetchall()
    return {row[0]: row[1] for row in result}


def shutdown_executor():
    """Shutdown the thread pool executor gracefully"""
    _query_executor.shutdown(wait=True)
