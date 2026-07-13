import csv
from pathlib import Path

from app.knowledge import list_learned_articles


DATA_DIR = Path(__file__).resolve().parents[1] / "outputs" / "krkrice_it_dataset" / "csv"


def read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_dataset() -> dict[str, list[dict[str, str]]]:
    return {
        "employees": read_csv("employees.csv"),
        "assets": read_csv("assets.csv"),
        "systems": read_csv("systems.csv"),
        "agents": read_csv("agents.csv"),
        "knowledge": [*read_csv("knowledge_articles.csv"), *list_learned_articles()],
        "tickets": read_csv("historical_tickets.csv"),
    }
