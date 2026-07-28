"""Timezone-aware time formatting utilities.

asyncpg always returns TIMESTAMPTZ values as UTC-aware datetimes regardless
of the PostgreSQL session timezone. This module provides a helper to convert
UTC datetimes to local (Beijing) time for API responses.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from core.config import settings

_LOCAL_TZ = ZoneInfo(settings.timezone)


def fmt_local_time(dt: datetime | None) -> str | None:
    """Convert a UTC-aware datetime to local time string for API output."""
    if not dt:
        return None
    return dt.astimezone(_LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
