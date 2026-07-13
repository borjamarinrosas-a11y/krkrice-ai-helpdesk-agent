import os
import re

from openai import OpenAI
from pydantic import BaseModel

from app.triage import CATEGORIES, TEAM_BY_CATEGORY


SOLUTION_MARKER = "KB SOLUTION:"


class KnowledgeDraft(BaseModel):
    title: str
    category: str
    system_id: str | None = None
    resolution_summary: str
    tags: list[str]


def find_verified_solution(comments: list[dict[str, str]]) -> dict[str, str]:
    candidates = [comment for comment in comments if SOLUTION_MARKER in comment["body"].upper()]
    if not candidates:
        raise ValueError(f"No comment containing '{SOLUTION_MARKER}' was found.")
    selected = candidates[-1]
    marker_position = selected["body"].upper().find(SOLUTION_MARKER)
    solution = selected["body"][marker_position + len(SOLUTION_MARKER):].strip()
    if len(solution) < 20:
        raise ValueError("The verified solution is too short to become a knowledge article.")
    return {**selected, "solution": solution}


def redact_sensitive_text(value: str) -> str:
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", value)
    value = re.sub(r"\b(?:sk|ATATT)[A-Za-z0-9_-]{16,}\b", "[secret removed]", value)
    value = re.sub(r"(?i)\b(password|token|secret)\s*[:=]\s*\S+", r"\1=[removed]", value)
    return value


def build_knowledge_draft(
    *,
    summary: str,
    description: str,
    solution: str,
    systems: list[dict[str, str]],
) -> KnowledgeDraft:
    clean_input = redact_sensitive_text(
        f"Ticket summary: {summary}\nDescription: {description}\nVerified solution: {solution}"
    )
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to generalize a learned solution.")
    system_catalog = ", ".join(f'{row["system_id"]}: {row["system_name"]}' for row in systems)
    response = OpenAI(api_key=api_key).responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        instructions=(
            "Convert a human-verified IT ticket solution into a concise reusable knowledge article. "
            f"Choose one category from: {', '.join(CATEGORIES)}. "
            "Generalize away employee names, dates, ticket IDs, credentials, and one-off details. "
            "Do not add steps that are absent from the verified solution. Use imperative troubleshooting steps. "
            "Choose system_id only from the provided catalog, otherwise null. Return 2-6 short lowercase tags."
        ),
        input=f"{clean_input}\n\nSystem catalog: {system_catalog}",
        text_format=KnowledgeDraft,
    )
    draft = response.output_parsed
    if draft is None or draft.category not in CATEGORIES:
        raise ValueError("OpenAI returned an invalid knowledge draft.")
    valid_system_ids = {row["system_id"] for row in systems}
    if draft.system_id not in valid_system_ids:
        draft.system_id = None
    draft.title = redact_sensitive_text(draft.title).strip()[:120]
    draft.resolution_summary = redact_sensitive_text(draft.resolution_summary).strip()
    draft.tags = [re.sub(r"[^a-z0-9-]", "", tag.lower()) for tag in draft.tags if tag][:6]
    if len(draft.resolution_summary) < 20:
        raise ValueError("The generated knowledge resolution is too short.")
    return draft


def owner_for_category(category: str) -> str:
    return TEAM_BY_CATEGORY[category][1]
