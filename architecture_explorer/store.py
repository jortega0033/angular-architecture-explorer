"""SQLite persistence for exploration projects."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone

SCHEMA_VERSION = 1
MAX_PROJECTS = 200

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  query TEXT NOT NULL,
  selected_path TEXT,
  selected_line INTEGER,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK ((selected_path IS NULL) = (selected_line IS NULL))
);
CREATE INDEX IF NOT EXISTS projects_updated ON projects(updated_at DESC, id);
"""

_COLUMNS = (
    "id, title, query, selected_path, selected_line, version, created_at, updated_at"
)


class SchemaVersionError(Exception):
    """Database was written by a newer version of the tool."""


class StorageError(Exception):
    """A database operation failed; no partial state was committed."""


class NotFound(Exception):
    pass


class Conflict(Exception):
    def __init__(self, current: dict) -> None:
        super().__init__("version conflict")
        self.current = current


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _row_to_project(row: tuple) -> dict:
    pid, title, query, spath, sline, version, created, updated = row
    selected = None if spath is None else {"path": spath, "line": sline}
    return {
        "id": pid,
        "title": title,
        "query": query,
        "selected": selected,
        "version": version,
        "created_at": created,
        "updated_at": updated,
    }


def _sel(selected: dict | None) -> tuple:
    if selected is None:
        return None, None
    return selected["path"], selected["line"]


class Store:
    """One shared connection guarded by a lock; explicit transactions."""

    def __init__(self, db_path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            db_path, check_same_thread=False, isolation_level=None, timeout=10.0
        )
        self._last = ""
        try:
            self._init_schema()
            row = self._conn.execute("SELECT MAX(updated_at) FROM projects").fetchone()
            self._last = row[0] or ""
        except BaseException:
            self._conn.close()
            raise

    def _init_schema(self) -> None:
        c = self._conn
        found = c.execute("PRAGMA user_version").fetchone()[0]
        if found > SCHEMA_VERSION:
            raise SchemaVersionError(
                f"database schema version {found} is newer than supported "
                f"version {SCHEMA_VERSION}"
            )
        c.execute("PRAGMA foreign_keys = ON")
        try:
            c.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:
            pass
        c.execute("PRAGMA synchronous = NORMAL")
        if found < SCHEMA_VERSION:
            c.execute("BEGIN IMMEDIATE")
            try:
                for stmt in _SCHEMA.split(";"):
                    if stmt.strip():
                        c.execute(stmt)
                c.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                c.execute("COMMIT")
            except BaseException:
                if c.in_transaction:
                    c.execute("ROLLBACK")
                raise

    def _stamp(self) -> str:
        """Strictly increasing millisecond timestamp; call with the lock held."""
        now = _now()
        if now <= self._last:
            prev = datetime.strptime(self._last, "%Y-%m-%dT%H:%M:%S.%fZ")
            now = (prev + timedelta(milliseconds=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        self._last = now
        return now

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass

    # -- helpers -----------------------------------------------------------
    def _get(self, pid: str) -> dict | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM projects WHERE id = ?", (pid,)
        ).fetchone()
        return _row_to_project(row) if row else None

    # -- operations --------------------------------------------------------
    def count(self) -> int:
        with self._lock:
            try:
                return self._conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            except sqlite3.Error as exc:
                raise StorageError(str(exc)) from exc

    def list(self) -> list[dict]:
        with self._lock:
            try:
                rows = self._conn.execute(
                    f"SELECT {_COLUMNS} FROM projects "
                    "ORDER BY updated_at DESC, id LIMIT ?",
                    (MAX_PROJECTS,),
                ).fetchall()
            except sqlite3.Error as exc:
                raise StorageError(str(exc)) from exc
        return [_row_to_project(r) for r in rows]

    def get(self, pid: str) -> dict | None:
        with self._lock:
            try:
                return self._get(pid)
            except sqlite3.Error as exc:
                raise StorageError(str(exc)) from exc

    def create(self, title: str, query: str, selected: dict | None) -> dict:
        pid = uuid.uuid4().hex
        spath, sline = _sel(selected)
        with self._lock:
            now = self._stamp()
            c = self._conn
            try:
                c.execute("BEGIN IMMEDIATE")
                try:
                    c.execute(
                        "INSERT INTO projects (id, title, query, selected_path, "
                        "selected_line, version, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                        (pid, title, query, spath, sline, now, now),
                    )
                    project = self._get(pid)
                    c.execute("COMMIT")
                except BaseException:
                    if c.in_transaction:
                        c.execute("ROLLBACK")
                    raise
            except sqlite3.Error as exc:
                raise StorageError(str(exc)) from exc
        assert project is not None
        return project

    def update(
        self, pid: str, version: int, title: str, query: str, selected: dict | None
    ) -> dict:
        """Optimistic update in one transaction. Raises NotFound / Conflict."""
        spath, sline = _sel(selected)
        with self._lock:
            now = self._stamp()
            c = self._conn
            try:
                c.execute("BEGIN IMMEDIATE")
                try:
                    current = self._get(pid)
                    if current is None:
                        c.execute("ROLLBACK")
                        raise NotFound()
                    if current["version"] != version:
                        c.execute("ROLLBACK")
                        raise Conflict(current)
                    cur = c.execute(
                        "UPDATE projects SET title = ?, query = ?, selected_path = ?, "
                        "selected_line = ?, version = version + 1, updated_at = ? "
                        "WHERE id = ? AND version = ?",
                        (title, query, spath, sline, now, pid, version),
                    )
                    if cur.rowcount != 1:
                        raise sqlite3.OperationalError("update affected no row")
                    project = self._get(pid)
                    c.execute("COMMIT")
                except (NotFound, Conflict):
                    raise
                except BaseException:
                    if c.in_transaction:
                        c.execute("ROLLBACK")
                    raise
            except sqlite3.Error as exc:
                raise StorageError(str(exc)) from exc
        assert project is not None
        return project
