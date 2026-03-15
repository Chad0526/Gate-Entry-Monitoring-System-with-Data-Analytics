"""
PostgreSQL backend that forces the connection timezone to UTC.
Use when the server default is not UTC so Django's utc_tzinfo_factory (USE_TZ) works.
Set ENGINE to 'gate_analytics.postgresql_utc' in DATABASES when using PostgreSQL.

If the connection timezone still cannot be set to UTC (e.g. server/config constraint),
query handles use a tzinfo_factory that never raises and always returns UTC so login
and queries work; stored timestamptz values are still correct instants.
"""
from django.utils.timezone import utc

try:
    from django.db.backends.postgresql import base as pg_base
except Exception:
    pg_base = None


def _safe_utc_tzinfo_factory(offset):
    """Like Django's utc_tzinfo_factory but never raises; always return UTC."""
    return utc


if pg_base is not None:
    class DatabaseWrapper(pg_base.DatabaseWrapper):
        @property
        def timezone_name(self):
            """Force UTC for this connection so Django's utc_tzinfo_factory does not raise."""
            return 'UTC'

        def init_connection_state(self):
            # Force UTC on the connection before any query handle is used.
            if self.connection is not None:
                with self.connection.cursor() as handle:
                    handle.execute("SET time zone 'UTC'")
            super().init_connection_state()

        def create_cursor(self, name=None):
            # Try to ensure session is UTC before each query handle.
            if self.connection is not None:
                with self.connection.cursor() as handle:
                    handle.execute("SET time zone 'UTC'")
            handle = super().create_cursor(name=name)
            # Use a factory that never raises so we work even if SET time zone didn't take effect.
            handle.tzinfo_factory = _safe_utc_tzinfo_factory
            return handle
else:
    from django.core.exceptions import ImproperlyConfigured

    class DatabaseWrapper:
        """Stub when psycopg2 is not installed; raises when used."""

        def __init__(self, *args, **kwargs):
            raise ImproperlyConfigured(
                "The PostgreSQL UTC engine requires psycopg2. "
                "Install it with: pip install psycopg2-binary"
            )
