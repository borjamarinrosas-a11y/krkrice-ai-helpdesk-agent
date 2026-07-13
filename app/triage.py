import os
import re
import unicodedata

from openai import OpenAI
from pydantic import BaseModel

from app.schemas import Match, TicketInput, TriageDecision


TEAM_BY_CATEGORY = {
    "Identity & Access": ("7e9e1a64-4bdf-40c1-a473-cb9a02f6fead", "KRkRice IT Access Management"),
    "Hardware": ("aa329d92-9705-4d88-8311-3cc63d5003b9", "KRkRice IT Service Desk"),
    "Collaboration": ("aa329d92-9705-4d88-8311-3cc63d5003b9", "KRkRice IT Service Desk"),
    "Service Request": ("aa329d92-9705-4d88-8311-3cc63d5003b9", "KRkRice IT Service Desk"),
    "Business Applications": ("28908fd5-ed85-41b4-b44b-a42ac6fd4d70", "KRkRice IT Business Applications"),
    "Network & VPN": ("74d73a91-96cf-4527-afda-222a74f4cc3a", "KRkRice IT Network & Infrastructure"),
    "Incident Management": ("74d73a91-96cf-4527-afda-222a74f4cc3a", "KRkRice IT Network & Infrastructure"),
    "Security": ("6b1c45e7-9341-45a9-9555-7efb6bb22fc2", "KRkRice IT Security"),
}

KEYWORDS = {
    "Security": {"phishing", "malware", "suspicious", "stolen", "lost", "compromise"},
    "Network & VPN": {"vpn", "wifi", "network", "forticlient", "connection", "connect"},
    "Identity & Access": {"password", "mfa", "login", "account", "locked", "access"},
    "Hardware": {"laptop", "monitor", "printer", "scanner", "dock", "screen", "tablet"},
    "Business Applications": {"riceflow", "graintrack", "exporthub", "certirice", "shiplink", "erp", "crm"},
    "Collaboration": {"teams", "sharepoint", "microphone", "document", "file"},
    "Service Request": {"install", "software", "onboard", "new employee", "request"},
}

CATEGORIES = tuple(TEAM_BY_CATEGORY)


class AIClassification(BaseModel):
    category: str
    priority: str
    confidence: float
    reasoning: str
    relevant_article_id: str | None = None
    article_relevance: float = 0.0


def tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return {word for word in re.findall(r"[a-z0-9]+", normalized) if len(word) > 2}


def similarity(query: str, candidate: str) -> float:
    left, right = tokens(query), tokens(candidate)
    if not left or not right:
        return 0.0
    # Retrieval should reward a source that covers the ticket vocabulary even
    # when the source contains a longer troubleshooting procedure.
    return len(left & right) / len(left)


def classify(text: str) -> tuple[str, float]:
    query = tokens(text)
    scored = [(category, len(query & words)) for category, words in KEYWORDS.items()]
    category, hits = max(scored, key=lambda item: item[1])
    if hits == 0:
        return "Business Applications", 0.45
    return category, min(0.65 + hits * 0.1, 0.95)


def classify_with_openai(
    text: str,
    systems: list[dict[str, str]],
    knowledge: list[dict[str, str]],
) -> tuple[str, str, float, str, str | None, float]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        category, confidence = classify(text)
        return category, "Medium", confidence, "Rules fallback: OPENAI_API_KEY is not available.", None, 0.0

    system_catalog = ", ".join(f'{row["system_name"]} ({row["category"]})' for row in systems)
    article_catalog = "\n".join(
        f'{row["article_id"]}: {row["title"]} — {row["resolution_summary"]}'
        for row in knowledge
        if row["status"] == "Published"
    )
    client = OpenAI(api_key=api_key)
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        instructions=(
            "You classify internal IT helpdesk tickets for the fictional company KRkRice. "
            f"Choose exactly one category from: {', '.join(CATEGORIES)}. "
            "Choose priority Low, Medium, High, or Critical. "
            "Security, phishing, malware, suspicious login, lost devices, and possible compromise are Security. "
            "An error inside a business workflow or business application is Business Applications even when "
            "the user mentions a screen. Use Hardware only for physical devices or peripherals. "
            "Also select relevant_article_id only when an article directly addresses the same problem and its "
            "procedure is appropriate. Matching only the application name is insufficient. For unknown error "
            "codes or different intents, return null and article_relevance 0."
        ),
        input=(
            f"Ticket:\n{text}\n\nKnown company systems:\n{system_catalog}"
            f"\n\nApproved knowledge articles:\n{article_catalog}"
        ),
        text_format=AIClassification,
    )
    parsed = response.output_parsed
    if parsed is None or parsed.category not in CATEGORIES:
        raise ValueError("OpenAI returned an invalid helpdesk category.")
    priority = parsed.priority if parsed.priority in {"Low", "Medium", "High", "Critical"} else "Medium"
    confidence = max(0.0, min(1.0, parsed.confidence))
    valid_articles = {row["article_id"]: row for row in knowledge if row["status"] == "Published"}
    article_id = parsed.relevant_article_id
    if article_id not in valid_articles or (article_id and valid_articles[article_id]["category"] != parsed.category):
        article_id = None
    relevance = max(0.0, min(1.0, parsed.article_relevance)) if article_id else 0.0
    return parsed.category, priority, confidence, parsed.reasoning, article_id, relevance


def title_coverage(query: str, title: str) -> float:
    query_tokens, title_tokens = tokens(query), tokens(title)
    if not query_tokens or not title_tokens:
        return 0.0
    return len(query_tokens & title_tokens) / len(title_tokens)


def deterministic_article_id(query: str, category: str) -> str | None:
    """Return only deliberately curated, high-precision intent matches."""
    query_tokens = tokens(query)
    if (
        category == "Network & VPN"
        and "vpn" in query_tokens
        and "password" in query_tokens
        and bool(query_tokens & {"change", "changed", "changing", "new"})
    ):
        return "KB-002"
    return None


def rank_knowledge(query: str, rows: list[dict[str, str]], category: str) -> list[Match]:
    matches = [
        Match(
            record_id=row["article_id"],
            title=row["title"],
            score=round(
                max(
                    similarity(query, f'{row["title"]} {row["resolution_summary"]}'),
                    title_coverage(query, row["title"]) * 0.8,
                ),
                3,
            ),
        )
        for row in rows
        if row["status"] == "Published" and row["category"] == category
    ]
    return sorted(matches, key=lambda match: match.score, reverse=True)[:3]


def rank_history(query: str, rows: list[dict[str, str]], category: str) -> list[Match]:
    matches = [
        Match(
            record_id=row["ticket_id"],
            title=row["summary"],
            score=round(similarity(query, f'{row["summary"]} {row["category"]} {row["business_impact"]} {row["resolution"]}'), 3),
        )
        for row in rows
        if row["status"] in {"Resolved", "Closed"} and row["resolution"] and row["category"] == category
    ]
    return sorted(matches, key=lambda match: match.score, reverse=True)[:3]


def make_decision(ticket: TicketInput, dataset: dict[str, list[dict[str, str]]]) -> TriageDecision:
    query = f"{ticket.summary} {ticket.description}".strip()
    classification_method = "rules"
    approved_article_id = None
    approved_article_relevance = 0.0
    if ticket.use_ai:
        try:
            (
                category,
                suggested_priority,
                classification_confidence,
                classification_note,
                approved_article_id,
                approved_article_relevance,
            ) = classify_with_openai(query, dataset["systems"], dataset["knowledge"])
            classification_method = "openai" if os.getenv("OPENAI_API_KEY") else "rules"
        except Exception as exc:
            category, classification_confidence = classify(query)
            suggested_priority = "Medium"
            classification_note = f"Rules fallback after OpenAI error: {type(exc).__name__}."
    else:
        category, classification_confidence = classify(query)
        suggested_priority = "Medium"
        classification_note = "Rules classifier requested by caller."
    knowledge = rank_knowledge(query, dataset["knowledge"], category)
    history = rank_history(query, dataset["tickets"], category)
    if approved_article_id:
        selected = next((match for match in knowledge if match.record_id == approved_article_id), None)
        if selected:
            selected.score = round(approved_article_relevance, 3)
            knowledge = [selected, *[match for match in knowledge if match.record_id != approved_article_id]]
    team_id, team_name = TEAM_BY_CATEGORY[category]

    system_id = None
    if knowledge and knowledge[0].score > 0:
        article = next(row for row in dataset["knowledge"] if row["article_id"] == knowledge[0].record_id)
        system_id = article["system_id"]

    priority = "Critical" if category == "Security" else suggested_priority
    best_score = knowledge[0].score if knowledge else 0.0
    confidence = round(min(0.98, classification_confidence * 0.55 + best_score * 0.9), 2)
    curated_article_id = deterministic_article_id(query, category)
    error_codes = set(re.findall(r"\b[A-Z]{2,}-\d+\b", query.upper()))
    top_article_text = ""
    if knowledge:
        top_article_row = next(
            row for row in dataset["knowledge"] if row["article_id"] == knowledge[0].record_id
        )
        top_article_text = f'{top_article_row["title"]} {top_article_row["resolution_summary"]}'.upper()
    exact_error_code_grounding = bool(error_codes) and all(code in top_article_text for code in error_codes)
    answer_is_grounded = (
        (approved_article_id is not None and approved_article_relevance >= 0.70)
        or (curated_article_id is not None and knowledge and knowledge[0].record_id == curated_article_id)
        or exact_error_code_grounding
        if classification_method == "openai"
        else best_score >= 0.30
    )
    if error_codes and not exact_error_code_grounding:
        # Error codes require an exact approved-code match. A general article
        # for the same application is not sufficient grounding.
        answer_is_grounded = False

    if category == "Security":
        decision = "escalate"
        response = None
        escalation = "Security tickets require mandatory human review."
    elif answer_is_grounded and confidence >= 0.65:
        decision = "respond"
        article = next(row for row in dataset["knowledge"] if row["article_id"] == knowledge[0].record_id)
        response = (
            f"Suggested internal draft based on {article['article_id']} ({article['title']}): "
            f"{article['resolution_summary']}"
        )
        escalation = None
    else:
        decision = "route"
        response = None
        escalation = "No sufficiently strong approved knowledge match was found."

    return TriageDecision(
        issue_key=ticket.issue_key,
        category=category,
        system_id=system_id,
        priority=priority,
        assigned_team_id=team_id,
        assigned_team_name=team_name,
        decision=decision,
        confidence=confidence,
        knowledge_matches=knowledge,
        historical_matches=history,
        suggested_response=response,
        escalation_reason=escalation,
        classification_method=classification_method,
        classification_note=classification_note,
    )
