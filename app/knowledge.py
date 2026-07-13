import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "knowledge.db"


def init_knowledge_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT UNIQUE,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                system_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner TEXT NOT NULL,
                resolution_summary TEXT NOT NULL,
                tags TEXT NOT NULL,
                source_issue_key TEXT NOT NULL UNIQUE,
                source_comment_id TEXT,
                verified_by TEXT NOT NULL
            )
            """
        )


def _article_from_row(row: sqlite3.Row) -> dict[str, str]:
    return {
        "article_id": row["article_id"],
        "title": row["title"],
        "category": row["category"],
        "system_id": row["system_id"] or "",
        "status": row["status"],
        "last_reviewed": row["created_at"][:10],
        "owner": row["owner"],
        "resolution_summary": row["resolution_summary"],
        "tags": row["tags"],
        "source_issue_key": row["source_issue_key"],
        "source_comment_id": row["source_comment_id"] or "",
        "verified_by": row["verified_by"],
    }


def list_learned_articles() -> list[dict[str, str]]:
    init_knowledge_db()
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM learned_articles ORDER BY id").fetchall()
    return [_article_from_row(row) for row in rows]


def normalized_words(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", value.lower()) if len(word) > 2}


def is_duplicate_article(title: str, resolution: str, articles: list[dict[str, str]]) -> bool:
    candidate = normalized_words(f"{title} {resolution}")
    if not candidate:
        return True
    for article in articles:
        existing = normalized_words(f"{article['title']} {article['resolution_summary']}")
        union = candidate | existing
        if union and len(candidate & existing) / len(union) >= 0.75:
            return True
    return False


def add_learned_article(
    *,
    title: str,
    category: str,
    system_id: str | None,
    owner: str,
    resolution_summary: str,
    tags: list[str],
    source_issue_key: str,
    source_comment_id: str | None,
    verified_by: str,
    existing_articles: list[dict[str, str]],
) -> dict[str, str]:
    init_knowledge_db()
    if is_duplicate_article(title, resolution_summary, existing_articles):
        raise ValueError("A sufficiently similar knowledge article already exists.")
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO learned_articles (
                    article_id, title, category, system_id, status, created_at,
                    owner, resolution_summary, tags, source_issue_key,
                    source_comment_id, verified_by
                ) VALUES (NULL, ?, ?, ?, 'Published', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(), category, system_id, created_at, owner,
                    resolution_summary.strip(), "|".join(sorted(set(tags))),
                    source_issue_key.upper(), source_comment_id, verified_by,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("This Jira issue has already produced a knowledge article.") from exc
        article_id = f"LKB-{cursor.lastrowid:04d}"
        connection.execute(
            "UPDATE learned_articles SET article_id = ? WHERE id = ?",
            (article_id, cursor.lastrowid),
        )
    return next(article for article in list_learned_articles() if article["article_id"] == article_id)
