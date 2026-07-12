import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "audit.db"


def init_audit_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                issue_key TEXT NOT NULL,
                event_type TEXT NOT NULL,
                action TEXT NOT NULL,
                category TEXT NOT NULL,
                assigned_agent_id TEXT NOT NULL,
                assigned_agent_name TEXT NOT NULL,
                assigned_team_id TEXT,
                assigned_team_name TEXT,
                comment_id TEXT,
                labels_json TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(audit_events)")}
        if "assigned_team_id" not in columns:
            connection.execute("ALTER TABLE audit_events ADD COLUMN assigned_team_id TEXT")
        if "assigned_team_name" not in columns:
            connection.execute("ALTER TABLE audit_events ADD COLUMN assigned_team_name TEXT")


def record_triage(
    *,
    issue_key: str,
    action: str,
    category: str,
    assigned_team_id: str,
    assigned_team_name: str,
    comment_id: str,
    labels: list[str],
    event_type: str = "approved_triage",
) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO audit_events (
                created_at, issue_key, event_type, action, category,
                assigned_agent_id, assigned_agent_name, assigned_team_id,
                assigned_team_name, comment_id, labels_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                issue_key,
                event_type,
                action,
                category,
                assigned_team_id,
                assigned_team_name,
                assigned_team_id,
                assigned_team_name,
                comment_id,
                json.dumps(labels),
            ),
        )


def record_approved_triage(**kwargs) -> None:
    record_triage(**kwargs, event_type="approved_triage")


def list_audit_events(limit: int = 50) -> list[dict[str, object]]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 200)),),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "issue_key": row["issue_key"],
            "event_type": row["event_type"],
            "action": row["action"],
            "category": row["category"],
            "assigned_team_id": row["assigned_team_id"] or row["assigned_agent_id"],
            "assigned_team_name": row["assigned_team_name"] or row["assigned_agent_name"],
            "comment_id": row["comment_id"],
            "labels": json.loads(row["labels_json"]),
        }
        for row in rows
    ]
