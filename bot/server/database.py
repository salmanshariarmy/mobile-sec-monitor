import json
import logging
import os
import sqlite3
import time

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


logger = logging.getLogger("database")


class Database:

    def __init__(self, db_path: str = None):

        if db_path is None:
            db_path = os.getenv(
                "DB_PATH",
                "data/threats.db"
            )

        self.db_path = db_path

        Path(db_path).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self._init_tables()
        self._migrate_tables()


    def _init_tables(self):

        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            severity TEXT DEFAULT 'MEDIUM',
            timestamp TEXT,
            details TEXT,
            agent_id TEXT,
            device_info TEXT
        );

        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            last_heartbeat TEXT,
            device_info TEXT,
            status TEXT DEFAULT 'offline',
            registered_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            command TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS blocked_numbers (
            number TEXT PRIMARY KEY,
            added_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS whitelisted_apps (
            package TEXT PRIMARY KEY,
            added_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_alerts_ts
        ON alerts(timestamp);
        """)

        self.conn.commit()


    def _migrate_tables(self):

        c = self.conn.cursor()

        c.execute(
            "PRAGMA table_info(agents)"
        )

        columns = {
            row["name"]
            for row in c.fetchall()
        }

        if "status" not in columns:
            c.execute(
                """
                ALTER TABLE agents
                ADD COLUMN status TEXT DEFAULT 'offline'
                """
            )

        if "registered_at" not in columns:
            c.execute(
                """
                ALTER TABLE agents
                ADD COLUMN registered_at TEXT
                """
            )

        self.conn.commit()


    def save_alert(self, alert: dict):

        c = self.conn.cursor()

        c.execute(
            """
            INSERT INTO alerts
            (
                title,
                description,
                severity,
                timestamp,
                details,
                agent_id,
                device_info
            )
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                alert.get("title","Alert"),
                alert.get("description",""),
                alert.get("severity","MEDIUM"),
                alert.get(
                    "timestamp",
                    time.strftime("%Y-%m-%dT%H:%M:%S")
                ),
                json.dumps(
                    alert.get("details",{})
                ),
                alert.get(
                    "agent_id",
                    "unknown"
                ),
                json.dumps(
                    alert.get(
                        "device_info",
                        {}
                    )
                )
            )
        )

        self.conn.commit()

        return c.lastrowid


    def get_alerts(
        self,
        limit=25,
        severity=None,
        agent_id=None
    ):

        c = self.conn.cursor()

        query = """
        SELECT *
        FROM alerts
        WHERE 1=1
        """

        params=[]

        if severity:
            query += " AND severity=?"
            params.append(
                severity.upper()
            )

        if agent_id:
            query += " AND agent_id=?"
            params.append(
                agent_id
            )

        query += """
        ORDER BY timestamp DESC
        LIMIT ?
        """

        params.append(limit)

        c.execute(
            query,
            params
        )

        return [
            dict(x)
            for x in c.fetchall()
        ]


    def count_alerts(self):

        c=self.conn.cursor()

        c.execute(
            "SELECT COUNT(*) AS c FROM alerts"
        )

        return c.fetchone()["c"]


    def register_agent(
        self,
        agent_id: str,
        device_info: dict = None
    ):

        try:

            c=self.conn.cursor()

            info=json.dumps(
                device_info or {}
            )

            c.execute(
                """
                INSERT INTO agents
                (
                    agent_id,
                    last_heartbeat,
                    device_info,
                    status
                )
                VALUES
                (
                    ?,
                    datetime('now'),
                    ?,
                    'online'
                )

                ON CONFLICT(agent_id)
                DO UPDATE SET

                    last_heartbeat=datetime('now'),

                    device_info=?,

                    status='online'
                """,
                (
                    agent_id,
                    info,
                    info
                )
            )

            self.conn.commit()


        except Exception as e:

            logger.exception(
                "register_agent failed: %s",
                e
            )

            raise


    def get_agents(self):

        c=self.conn.cursor()

        c.execute(
            """
            SELECT *
            FROM agents
            ORDER BY last_heartbeat DESC
            """
        )

        return [
            dict(x)
            for x in c.fetchall()
        ]


    def get_agent(
        self,
        agent_id:str
    ) -> Optional[dict]:

        c=self.conn.cursor()

        c.execute(
            """
            SELECT *
            FROM agents
            WHERE agent_id=?
            """,
            (agent_id,)
        )

        row=c.fetchone()

        return dict(row) if row else None


    def queue_command(
        self,
        agent_id,
        command
    ):

        self.conn.execute(
            """
            INSERT INTO commands
            (
                agent_id,
                command
            )
            VALUES (?,?)
            """,
            (
                agent_id,
                command
            )
        )

        self.conn.commit()


    def get_pending_commands(
        self,
        agent_id
    ):

        c=self.conn.cursor()

        c.execute(
            """
            SELECT *
            FROM commands
            WHERE agent_id=?
            AND status='pending'
            ORDER BY created_at ASC
            """,
            (agent_id,)
        )

        cmds=[
            dict(x)
            for x in c.fetchall()
        ]

        for cmd in cmds:

            c.execute(
                """
                UPDATE commands
                SET status='executed'
                WHERE id=?
                """,
                (cmd["id"],)
            )

        self.conn.commit()

        return cmds


    def add_blocked_number(
        self,
        number
    ):

        self.conn.execute(
            """
            INSERT OR IGNORE INTO blocked_numbers(number)
            VALUES(?)
            """,
            (number,)
        )

        self.conn.commit()


    def add_whitelisted_app(
        self,
        package
    ):

        self.conn.execute(
            """
            INSERT OR IGNORE INTO whitelisted_apps(package)
            VALUES(?)
            """,
            (package,)
        )

        self.conn.commit()
