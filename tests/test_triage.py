from fastapi.testclient import TestClient

from app.main import app, label_slug
from app.jira import adf_to_text, text_to_adf


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
