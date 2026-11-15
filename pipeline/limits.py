"""Explicit resource budgets, shared by private ingestion and HTTP ingestion."""
import os
from . import config  # Configuration must be loaded before resource settings are read.
import threading
from contextlib import contextmanager

QUERY_SLOTS = threading.BoundedSemaphore(4)

def positive_setting(name, default):
    try:
        value = int(os.environ.get(name, default))
        if value > 0:
            return value
    except ValueError:
        pass
    # Report the setting name, never its potentially sensitive value.
    raise ValueError(f'{name} must be a positive integer') from None


MAX_FILE_BYTES = positive_setting('FIRE_MAX_FILE_BYTES', 64 * 1024 * 1024)
MAX_OBSERVATIONS = positive_setting('FIRE_MAX_OBSERVATIONS', 1_000_000)
MAX_CACHE_BYTES = positive_setting('FIRE_MAX_CACHE_BYTES', 1024 * 1024 * 1024)
RETENTION_DAYS = positive_setting('FIRE_CACHE_RETENTION_DAYS', 7)


@contextmanager
def connection():
    import duckdb
    from fastapi import HTTPException
    if not QUERY_SLOTS.acquire(timeout=1):
        raise HTTPException(503, 'Query capacity reached; retry later')
    try:
        with duckdb.connect(config={'memory_limit': '256MB', 'threads': 2,
                                    'max_temp_directory_size': '256MB'}) as db:
            yield db
    finally:
        QUERY_SLOTS.release()
