# KRkRice Autonomous Helpdesk Agent

Portfolio project for a fictional rice exporter in Kraków. The service monitors Jira,
classifies IT requests with OpenAI, retrieves approved internal knowledge, takes a safe
action, routes work to stable Jira Teams, and records every decision for review.

## Architecture

```text
Jira ticket
    ↓
OpenAI classification + deterministic safety rules
    ↓
Approved knowledge and resolved-ticket retrieval
    ↓
respond publicly | route internally | escalate securely
    ↓
Jira Team assignment + labels + SQLite audit event
    ↓
KRkRice control-room dashboard
```

## Current MVP

- Loads the generated KRkRice CSV dataset.
- Classifies incoming tickets.
- Retrieves relevant knowledge articles and resolved tickets.
- Returns a structured triage decision.
- Blocks automatic responses for security cases.
- Can read an existing `SUP` Jira ticket and triage it without modifying Jira.
- Requires an explicit `PUBLISH` confirmation before adding an internal Jira comment.
- Lists pending Jira issues that have not yet received the `ai-triaged` label.
- Builds a read-only review queue with AI previews for all pending tickets.
- Applies an approved comment and routing labels in one guarded operation.
- Stores approved combined actions in a local SQLite audit log.
- Routes to stable Jira Teams rather than individual agents, so staffing can change without changing the AI logic.

## Routing model

| Ticket category | Jira Team |
| --- | --- |
| Identity & Access | KRkRice IT Access Management |
| Hardware, Collaboration, Service Request | KRkRice IT Service Desk |
| Business Applications | KRkRice IT Business Applications |
| Network & VPN, Incident Management | KRkRice IT Network & Infrastructure |
| Security | KRkRice IT Security |

Team membership is managed in Atlassian. Replacing an employee does not require a code,
prompt, or model change.

## Safety policy

- `respond`: only a strongly grounded approved solution becomes a public reply.
- `route`: unknown or insufficiently grounded cases receive an internal note and Team assignment.
- `escalate`: security cases receive an internal escalation and never an automated solution.
- Unknown error codes cannot use a generic application article as an answer.
- `ai-triaged` prevents duplicate processing; every executed action is stored in the audit log.

## Run locally

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --reload-dir app
```

Open `http://127.0.0.1:8000/docs` to use the interactive API.

Open `http://127.0.0.1:8000/` for the visual audit dashboard.

Watch the human-review queue without writing to Jira:

```bash
python scripts/watch_review_queue.py --interval 30
```

Run the autonomous worker (this writes comments and routing labels to Jira):

```bash
python scripts/run_autonomous_agent.py --interval 30
```

In autonomous mode, grounded `respond` decisions create a public requester reply.
`route` and `escalate` decisions create internal notes only. Every action is audited.

## Test suite

```bash
python -m pytest -q
```

The repository uses synthetic company data only. Keep `.env` private; it contains the
OpenAI key and Jira API credentials and is excluded from version control.
