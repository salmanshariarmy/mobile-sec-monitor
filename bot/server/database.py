"""
SQLite database for threat storage and analytics.
"""
import sqlite3
import json
import datetime
import threading
from pathlib import Path
from typing import Optional

from config import Config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS threats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'MEDIUM',
    details     TEXT DEFAULT '{}',
    timestamp   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id    TEXT PRIMARY KEY,
    last_seen   TEXT,
    device_info TEXT DEFAULT '{}',
    status      TEXT DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_threats_severity ON threats(severity);
CREATE INDEX IF NOT EXISTS idx_threats_timestamp ON threats(timestamp);
CREATE INDEX IF NOT EXISTS idx_threats_agent ON threats(agent_id);
"""


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with _lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def insert_threat(self, agent_id: str, title: str, description: str,
                      severity: str, details: dict, timestamp: str) -> int:
        with _lock:
            cur = self._conn.execute(
                """INSERT INTO threats (agent_id, title, description, severity, details, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (agent_id, title, description, severity.upper(),
                 json.dumps(details), timestamp)
            )
            self._conn.commit()
            return cur.lastrowid

    def get_recent_threats(self, limit: int = 25, offset: int = 0,
                           severity: Optional[str] = None,
                           agent_id: Optional[str] = None) -> list:
        query = "SELECT * FROM threats WHERE 1=1"
        params = []
        if severity:
            query += " AND severity = ?"
            params.append(severity.upper())
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with _lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_threat_summary(self, hours: int = 24) -> dict:
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat()
        with _lock:
            rows = self._conn.execute(
                """SELECT severity, COUNT(*) as cnt
                   FROM threats
                   WHERE timestamp > ?
                   GROUP BY severity""",
                (cutoff,)
            ).fetchall()
        summary = {"total": 0, "CRITICAL": 0, "HIGH": 0,
                   "MEDIUM": 0, "LOW": 0, "INFO": 0, "hours": hours}
        for r in rows:
            sev = r["severity"]
            cnt = r["cnt"]
            summary[sev] = cnt
            summary["total"] += cnt
        return summary

    def upsert_agent(self, agent_id: str, device_info: dict = None):
        with _lock:
            now = datetime.datetime.utcnow().isoformat()
            info_str = json.dumps(device_info) if device_info else "{}"
            self._conn.execute(
                """INSERT INTO agents (agent_id, last_seen, device_info, status)
                   VALUES (?, ?, ?, 'active')
                   ON CONFLICT(agent_id) DO UPDATE SET
                       last_seen = excluded.last_seen,
                       device_info = excluded.device_info,
                       status = 'active'""",
                (agent_id, now, info_str)
            )
            self._conn.commit()

    def get_agents(self) -> list:
        with _lock:
            rows = self._conn.execute(
                "SELECT * FROM agents ORDER BY last_seen DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._conn.close()
