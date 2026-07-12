import os
from typing import Any

import httpx


class JiraConfigurationError(RuntimeError):
    pass


class JiraRequestError(RuntimeError):
    pass


def adf_to_text(node: Any) -> str:
    """Extract plain text from Atlassian Document Format."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return " ".join(part for item in node if (part := adf_to_text(item)))
    if not isinstance(node, dict):
        return ""
    own_text = node.get("text", "")
    child_text = adf_to_text(node.get("content", []))
    return " ".join(part for part in (own_text, child_text) if part).strip()


def text_to_adf(text: str) -> dict[str, Any]:
    paragraphs = []
    for line in text.splitlines():
        content = [{"type": "text", "text": line}] if line else []
        paragraphs.append({"type": "paragraph", "content": content})
    return {"type": "doc", "version": 1, "content": paragraphs or [{"type": "paragraph", "content": []}]}


def get_jira_issue(issue_key: str) -> dict[str, Any]:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    api_token = os.getenv("JIRA_API_TOKEN", "")
    project_key = os.getenv("JIRA_PROJECT_KEY", "SUP").upper()

    if not all((base_url, email, api_token)):
        raise JiraConfigurationError("Jira credentials are incomplete in .env.")
    if not issue_key.upper().startswith(f"{project_key}-"):
        raise JiraRequestError(f"Only issues from project {project_key} are allowed.")

    url = f"{base_url}/rest/api/3/issue/{issue_key.upper()}"
    try:
        response = httpx.get(
            url,
            params={"fields": "summary,description,priority,status,issuetype,reporter,labels"},
            auth=(email, api_token),
            headers={"Accept": "application/json"},
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise JiraRequestError(f"Jira returned HTTP {exc.response.status_code}.") from exc
    except httpx.HTTPError as exc:
        raise JiraRequestError("Could not connect to Jira.") from exc

    fields = response.json().get("fields", {})
    reporter = fields.get("reporter") or {}
    return {
        "issue_key": issue_key.upper(),
        "summary": fields.get("summary") or "",
        "description": adf_to_text(fields.get("description")),
        "jira_priority": (fields.get("priority") or {}).get("name", ""),
        "jira_status": (fields.get("status") or {}).get("name", ""),
        "reporter_name": reporter.get("displayName", ""),
        "labels": fields.get("labels") or [],
    }


def add_comment(issue_key: str, body: str, *, internal: bool) -> str:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    api_token = os.getenv("JIRA_API_TOKEN", "")
    project_key = os.getenv("JIRA_PROJECT_KEY", "SUP").upper()

    if not all((base_url, email, api_token)):
        raise JiraConfigurationError("Jira credentials are incomplete in .env.")
    if not issue_key.upper().startswith(f"{project_key}-"):
        raise JiraRequestError(f"Only issues from project {project_key} are allowed.")

    service_url = f"{base_url}/rest/servicedeskapi/request/{issue_key.upper()}/comment"
    try:
        response = httpx.post(
            service_url,
            json={"body": body, "public": not internal},
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=20.0,
        )
        if response.status_code == 404:
            # Issues created through the Jira platform API may not have a JSM
            # customer-request record. The platform comment API can still mark
            # the note internal through the official JSM comment property.
            platform_url = f"{base_url}/rest/api/3/issue/{issue_key.upper()}/comment"
            response = httpx.post(
                platform_url,
                json={
                    "body": text_to_adf(body),
                    "properties": [
                        {"key": "sd.public.comment", "value": {"internal": internal}},
                    ],
                },
                auth=(email, api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=20.0,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise JiraRequestError(f"Jira returned HTTP {exc.response.status_code} while adding the internal comment.") from exc
    except httpx.HTTPError as exc:
        raise JiraRequestError("Could not connect to Jira while adding the internal comment.") from exc

    return str(response.json().get("id", "unknown"))


def add_internal_comment(issue_key: str, body: str) -> str:
    return add_comment(issue_key, body, internal=True)


def add_public_comment(issue_key: str, body: str) -> str:
    return add_comment(issue_key, body, internal=False)


def add_labels(issue_key: str, labels: list[str]) -> list[str]:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    api_token = os.getenv("JIRA_API_TOKEN", "")
    project_key = os.getenv("JIRA_PROJECT_KEY", "SUP").upper()
    if not all((base_url, email, api_token)):
        raise JiraConfigurationError("Jira credentials are incomplete in .env.")
    if not issue_key.upper().startswith(f"{project_key}-"):
        raise JiraRequestError(f"Only issues from project {project_key} are allowed.")

    issue = get_jira_issue(issue_key)
    current = set(issue.get("labels", []))
    added = sorted(set(labels) - current)
    if not added:
        return []

    url = f"{base_url}/rest/api/3/issue/{issue_key.upper()}"
    try:
        response = httpx.put(
            url,
            json={"fields": {"labels": sorted(current | set(labels))}},
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise JiraRequestError(f"Jira returned HTTP {exc.response.status_code} while adding routing labels.") from exc
    except httpx.HTTPError as exc:
        raise JiraRequestError("Could not connect to Jira while adding routing labels.") from exc
    return added


def assign_team(issue_key: str, team_id: str) -> None:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    api_token = os.getenv("JIRA_API_TOKEN", "")
    if not all((base_url, email, api_token)):
        raise JiraConfigurationError("Jira credentials are incomplete in .env.")
    url = f"{base_url}/rest/api/3/issue/{issue_key.upper()}"
    try:
        response = httpx.put(
            url,
            json={"fields": {"customfield_10001": team_id}},
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise JiraRequestError(f"Jira returned HTTP {exc.response.status_code} while assigning the team.") from exc
    except httpx.HTTPError as exc:
        raise JiraRequestError("Could not connect to Jira while assigning the team.") from exc


def list_pending_issues(limit: int = 10) -> list[dict[str, str]]:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    api_token = os.getenv("JIRA_API_TOKEN", "")
    project_key = os.getenv("JIRA_PROJECT_KEY", "SUP").upper()
    if not all((base_url, email, api_token)):
        raise JiraConfigurationError("Jira credentials are incomplete in .env.")

    url = f"{base_url}/rest/api/3/search/jql"
    jql = (
        f'project = "{project_key}" AND issuetype != "Task" '
        'AND (labels IS EMPTY OR labels NOT IN ("ai-triaged")) ORDER BY created ASC'
    )
    try:
        response = httpx.post(
            url,
            json={
                "jql": jql,
                "maxResults": max(1, min(limit, 50)),
                "fields": ["summary", "status", "priority", "created"],
            },
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise JiraRequestError(f"Jira returned HTTP {exc.response.status_code} while listing pending issues.") from exc
    except httpx.HTTPError as exc:
        raise JiraRequestError("Could not connect to Jira while listing pending issues.") from exc

    pending = []
    for issue in response.json().get("issues", []):
        fields = issue.get("fields", {})
        pending.append(
            {
                "issue_key": issue.get("key", ""),
                "summary": fields.get("summary") or "",
                "status": (fields.get("status") or {}).get("name", ""),
                "priority": (fields.get("priority") or {}).get("name", ""),
                "created": fields.get("created") or "",
            }
        )
    return pending
