"""Persistent storage: SQLite database for verification graph, versioning, and metadata.

The NEXUS_HOME directory stores:
  - nexus.db: SQLite database (claims, verifications, waypoint_versions)
  - verigraph.jsonl: Append-only JSON-lines (legacy fallback if DB unavailable)
"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", Path.home() / ".nexus"))
DB_PATH = NEXUS_HOME / "nexus.db"


def ensure_nexus_home() -> Path:
    """Create NEXUS_HOME if it doesn't exist."""
    NEXUS_HOME.mkdir(parents=True, exist_ok=True)
    return NEXUS_HOME


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get or create SQLite connection, initializing schema if needed."""
    if db_path is None:
        db_path = DB_PATH
    ensure_nexus_home()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Initialize database schema if tables don't exist."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            waypoint_id TEXT NOT NULL,
            action_index INTEGER NOT NULL,
            strategy TEXT NOT NULL,
            value TEXT NOT NULL,
            role TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            event_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            dom_fingerprint TEXT NOT NULL,
            success INTEGER NOT NULL,
            evidence_type TEXT DEFAULT 'action',
            latency_ms REAL,
            error TEXT,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waypoint_versions (
            local_hash TEXT PRIMARY KEY,
            ipfs_hash TEXT,
            parent_hash TEXT,
            chain_version INTEGER DEFAULT 1,
            url TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_verifications_claim_id
        ON verifications(claim_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_waypoint_versions_parent
        ON waypoint_versions(parent_hash)
    """)

    conn.commit()


@contextmanager
def db_session(db_path: Optional[Path] = None):
    """Context manager for database transactions."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
