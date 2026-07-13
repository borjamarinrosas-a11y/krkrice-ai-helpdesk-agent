from fastapi.testclient import TestClient

from app.main import app, label_slug
from app.jira import adf_to_text, text_to_adf
from app.knowledge import add_learned_article, list_learned_articles
from app.learning import find_verified_solution, redact_sensitive_text
from app.schemas import TicketInput


def test_health_loads_dataset():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["records"]["tickets"] == 100


def test_dashboard_is_available():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "AI Helpdesk Control Room" in response.text


def test_vpn_ticket_is_routed_to_network_team():
    ticket = {
        "issue_key": "SUP-TEST",
        "summary": "VPN authentication failed after password change",
        "description": "FortiClient cannot connect to the company network.",
        "requester_employee_id": "EMP-042",
        "use_ai": False,
    }
    with TestClient(app) as client:
        response = client.post("/api/triage", json=ticket)
    body = response.json()
    assert response.status_code == 200
    assert body["category"] == "Network & VPN"
    assert body["assigned_team_name"] == "KRkRice IT Network & Infrastructure"
    assert body["knowledge_matches"][0]["record_id"] == "KB-002"
    assert body["decision"] == "respond"
    assert body["suggested_response"] is not None


def test_security_ticket_never_auto_responds():
    ticket = {
        "issue_key": "SUP-SEC",
        "summary": "Suspicious phishing email",
        "description": "A finance employee clicked a suspicious invoice link.",
        "use_ai": False,
    }
    with TestClient(app) as client:
        response = client.post("/api/triage", json=ticket)
    body = response.json()
    assert body["decision"] == "escalate"
    assert body["assigned_team_name"] == "KRkRice IT Security"
    assert body["suggested_response"] is None


def test_unknown_error_routes_without_inventing_a_solution():
    ticket = {
        "issue_key": "SUP-UNKNOWN",
        "summary": "The export planning screen shows error XR-917",
        "description": "The problem started today and we have never seen this error before.",
        "requester_employee_id": "EMP-020",
        "use_ai": False,
    }
    with TestClient(app) as client:
        response = client.post("/api/triage", json=ticket)
    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "route"
    assert body["suggested_response"] is None


def test_curated_vpn_intent_survives_ai_article_omission(monkeypatch):
    monkeypatch.setattr(
        "app.triage.classify_with_openai",
        lambda text, systems, knowledge: (
            "Network & VPN",
            "Medium",
            0.95,
            "VPN ticket, but model omitted the article identifier.",
            None,
            0.0,
        ),
    )
    ticket = {
        "issue_key": "SUP-VPN",
        "summary": "VPN credentials after password change",
        "description": "VPN rejects my new password and cached credentials must be refreshed.",
        "use_ai": True,
    }
    with TestClient(app) as client:
        response = client.post("/api/triage", json=ticket)
    body = response.json()
    assert response.status_code == 200
    assert body["knowledge_matches"][0]["record_id"] == "KB-002"
    assert body["decision"] == "respond"


def test_unknown_error_code_never_responds_even_if_ai_selects_article(monkeypatch):
    monkeypatch.setattr(
        "app.triage.classify_with_openai",
        lambda text, systems, knowledge: (
            "Business Applications",
            "Medium",
            0.98,
            "RiceFlow application issue.",
            "KB-011",
            0.95,
        ),
    )
    ticket = {
        "issue_key": "SUP-RF999",
        "summary": "RiceFlow export screen shows error RF-999",
        "description": "Unknown error started today.",
        "use_ai": True,
    }
    with TestClient(app) as client:
        response = client.post("/api/triage", json=ticket)
    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "route"
    assert body["suggested_response"] is None


def test_verified_learned_article_unlocks_exact_error_code(monkeypatch):
    monkeypatch.setattr(
        "app.triage.classify_with_openai",
        lambda text, systems, knowledge: (
            "Business Applications", "Medium", 0.95,
            "RiceFlow error with an exact verified article.", None, 0.0,
        ),
    )
    from app.repository import load_dataset
    dataset = load_dataset()
    dataset["knowledge"].append({
        "article_id": "LKB-TEST",
        "title": "Resolve RiceFlow export error RF-1000",
        "category": "Business Applications",
        "system_id": "SYS-002",
        "status": "Published",
        "last_reviewed": "2026-07-13",
        "owner": "KRkRice IT Business Applications",
        "resolution_summary": "Clear the failed export job, validate the batch, and retry once.",
        "tags": "riceflow|export",
    })
    ticket = TicketInput(
        issue_key="SUP-NEW",
        summary="RiceFlow export screen shows error RF-1000",
        description="The export failed today.",
        use_ai=True,
    )
    from app.triage import make_decision
    decision = make_decision(ticket, dataset)
    assert decision.knowledge_matches[0].record_id in {"LKB-0001", "LKB-TEST"}
    assert decision.decision == "respond"


def test_adf_description_is_converted_to_plain_text():
    description = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "VPN failed"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "after password change"}]},
        ],
    }
    assert adf_to_text(description) == "VPN failed after password change"


def test_plain_text_comment_is_converted_to_adf():
    adf = text_to_adf("AI triage\nInternal note")
    assert adf["type"] == "doc"
    assert adf["content"][0]["content"][0]["text"] == "AI triage"
    assert adf["content"][1]["content"][0]["text"] == "Internal note"


def test_routing_category_becomes_safe_jira_label():
    assert label_slug("Network & VPN") == "network-vpn"


def test_long_jira_vpn_description_still_retrieves_vpn_article():
    ticket = {
        "issue_key": "SUP-1",
        "summary": "Unable to connect to company VPN",
        "description": (
            "Synthetic helpdesk test invented employee Finance device laptop. "
            "FortiClient displays Authentication failed after the employee changed their password. "
            "Expected agent behavior classify access VPN and escalate account lockout."
        ),
        "use_ai": False,
    }
    with TestClient(app) as client:
        response = client.post("/api/triage", json=ticket)
    body = response.json()
    assert body["knowledge_matches"][0]["record_id"] == "KB-002"
    assert body["decision"] == "respond"


def test_preview_never_claims_it_will_write(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.main.get_jira_issue",
        lambda issue_key: {
            "issue_key": issue_key,
            "summary": "VPN authentication failed after password change",
            "description": "FortiClient cannot connect with the new password.",
        },
    )
    with TestClient(app) as client:
        response = client.post("/api/jira/SUP-1/preview")
    body = response.json()
    assert response.status_code == 200
    assert body["will_write_to_jira"] is False
    assert body["action"] == "add_internal_comment"
    assert "KB-002" in body["comment"]


def test_autonomous_run_publishes_and_audits_pending_ticket(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.main.list_pending_issues", lambda limit: [{"issue_key": "SUP-12"}])
    monkeypatch.setattr(
        "app.main.get_jira_issue",
        lambda issue_key: {
            "issue_key": issue_key,
            "summary": "VPN authentication failed after password change",
            "description": "FortiClient cannot connect with the new password.",
            "labels": [],
        },
    )
    published = []
    monkeypatch.setattr("app.main.add_public_comment", lambda issue_key, body: published.append(body) or "10071")
    monkeypatch.setattr("app.main.add_internal_comment", lambda issue_key, body: "internal")
    monkeypatch.setattr("app.main.add_labels", lambda issue_key, labels: labels)
    monkeypatch.setattr("app.main.assign_team", lambda issue_key, team_id: None)
    recorded = []
    monkeypatch.setattr("app.main.record_triage", lambda **kwargs: recorded.append(kwargs))

    with TestClient(app) as client:
        response = client.post(
            "/api/jira/autonomous-run",
            params={"limit": 10},
            json={"confirm": "RUN_AUTONOMOUS"},
        )

    body = response.json()[0]
    assert response.status_code == 200
    assert body["decision"] == "respond"
    assert body["action"] == "add_public_comment"
    assert body["status"] == "autonomously_published"
    assert "ai-autonomous" in body["labels_added"]
    assert published and "Hello," in published[0]
    assert "AI triage preview" not in published[0]
    assert recorded[0]["event_type"] == "autonomous_triage"


def test_autonomous_run_requires_explicit_confirmation():
    with TestClient(app) as client:
        response = client.post(
            "/api/jira/autonomous-run",
            json={"confirm": "PUBLISH"},
        )
    assert response.status_code == 422


def test_verified_solution_can_be_stored_as_learned_knowledge(monkeypatch, tmp_path):
    monkeypatch.setattr("app.knowledge.DB_PATH", tmp_path / "knowledge.db")
    article = add_learned_article(
        title="Resolve RiceFlow error RF-1000",
        category="Business Applications",
        system_id="SYS-011",
        owner="KRkRice IT Business Applications",
        resolution_summary="Clear the stuck export job, validate the batch, and retry once.",
        tags=["riceflow", "export"],
        source_issue_key="SUP-17",
        source_comment_id="10100",
        verified_by="team-lead",
        existing_articles=[],
    )
    assert article["article_id"] == "LKB-0001"
    assert article["status"] == "Published"
    assert list_learned_articles()[0]["source_issue_key"] == "SUP-17"


def test_similar_solution_is_rejected_as_duplicate(monkeypatch, tmp_path):
    monkeypatch.setattr("app.knowledge.DB_PATH", tmp_path / "knowledge.db")
    existing = [{
        "title": "Resolve RiceFlow export error",
        "resolution_summary": "Clear the stuck export job and retry the validated batch.",
    }]
    try:
        add_learned_article(
            title="Resolve RiceFlow export error",
            category="Business Applications",
            system_id="SYS-011",
            owner="KRkRice IT Business Applications",
            resolution_summary="Clear the stuck export job and retry the validated batch.",
            tags=["riceflow"],
            source_issue_key="SUP-20",
            source_comment_id="10101",
            verified_by="team-lead",
            existing_articles=existing,
        )
    except ValueError as exc:
        assert "similar" in str(exc)
    else:
        raise AssertionError("Expected duplicate knowledge to be rejected.")


def test_learning_requires_explicit_solution_marker():
    comments = [
        {"comment_id": "1", "body": "Restarted the service.", "author": "Aisha"},
        {"comment_id": "2", "body": "KB SOLUTION: Clear the failed batch and retry the validated export.", "author": "Lead"},
    ]
    selected = find_verified_solution(comments)
    assert selected["comment_id"] == "2"
    assert selected["verified_by"] if "verified_by" in selected else selected["author"] == "Lead"
    assert selected["solution"].startswith("Clear the failed batch")


def test_learning_redacts_credentials_and_email():
    text = "Contact person@example.com with password: SuperSecret and token=ATATTabcdefghijklmnop"
    redacted = redact_sensitive_text(text)
    assert "person@example.com" not in redacted
    assert "SuperSecret" not in redacted
    assert "ATATTabcdefghijklmnop" not in redacted


def test_learning_run_requires_explicit_confirmation():
    with TestClient(app) as client:
        response = client.post(
            "/api/jira/learning-run",
            json={"confirm": "RUN_AUTONOMOUS"},
        )
    assert response.status_code == 422
