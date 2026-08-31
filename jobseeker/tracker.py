import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

STATUSES = ["saved", "tailored", "applied", "interviewing", "offer", "rejected"]


@contextmanager
def _connect():
    config.ensure_dirs()
    conn = sqlite3.connect(str(config.TRACKER_DB_PATH))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                job_id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                url TEXT,
                status TEXT NOT NULL DEFAULT 'saved',
                updated_at TEXT NOT NULL
            )
            """
        )
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert(job_id: str, title: str, company: str, url: str, status: str = "saved") -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO applications (job_id, title, company, url, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                title=excluded.title, company=excluded.company, url=excluded.url,
                updated_at=excluded.updated_at
            """,
            (job_id, title, company, url, status, datetime.now(timezone.utc).isoformat()),
        )


def set_status(job_id: str, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Unknown status '{status}'. Valid: {', '.join(STATUSES)}")
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE job_id = ?",
            (status, datetime.now(timezone.utc).isoformat(), job_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"No tracked application with job_id '{job_id}'")


def list_all() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
