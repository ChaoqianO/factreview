"""Thread-safe database connection pool for parallel processing."""

from __future__ import annotations
import logging
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Per-thread SQLite connections (SQLite requires this for thread safety)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()

    def get(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    @contextmanager
    def connection(self):
        yield self.get()

    def close_thread(self):
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None


class ThreadSafeDBChecker:
    """Wraps LocalDBChecker to use per-thread database connections."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._pool = ConnectionPool(db_path)

    def verify_reference(self, reference):
        from .checkers.local_db import LocalDBChecker
        checker = LocalDBChecker.__new__(LocalDBChecker)
        checker.db_path = self.db_path
        checker.conn = self._pool.get()
        return checker.verify_reference(reference)

    def close(self):
        self._pool.close_thread()
