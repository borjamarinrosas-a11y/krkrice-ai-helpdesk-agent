from typing import Literal

from pydantic import BaseModel, Field


class TicketInput(BaseModel):
    issue_key: str = Field(min_length=1, examples=["SUP-101"])
    summary: str = Field(min_length=3)
    description: str = ""
    requester_employee_id: str | None = None
    use_ai: bool = True


class Match(BaseModel):
    record_id: str
    title: str
    score: float


class TriageDecision(BaseModel):
    issue_key: str
    category: str
    system_id: str | None
    priority: Literal["Low", "Medium", "High", "Critical"]
    assigned_team_id: str
    assigned_team_name: str
    decision: Literal["respond", "route", "escalate"]
    confidence: float = Field(ge=0, le=1)
    knowledge_matches: list[Match]
    historical_matches: list[Match]
    suggested_response: str | None
    escalation_reason: str | None
    classification_method: Literal["openai", "rules"]
    classification_note: str


class JiraCommentPreview(BaseModel):
    issue_key: str
    action: Literal["add_internal_comment", "route_only", "escalate"]
    comment: str
    will_write_to_jira: bool = False


class PublishConfirmation(BaseModel):
    confirm: Literal["PUBLISH"]


class AutonomousConfirmation(BaseModel):
    confirm: Literal["RUN_AUTONOMOUS"]


class JiraCommentResult(BaseModel):
    issue_key: str
    comment_id: str
    internal: bool = True
    status: Literal["published"] = "published"


class JiraRoutingResult(BaseModel):
    issue_key: str
    labels_added: list[str]
    status: Literal["published"] = "published"


class PendingJiraIssue(BaseModel):
    issue_key: str
    summary: str
    status: str
    priority: str
    created: str


class ApprovedTriageResult(BaseModel):
    issue_key: str
    action: Literal["add_internal_comment", "route_only", "escalate"]
    comment_id: str
    labels_added: list[str]
    status: Literal["approved_and_published"] = "approved_and_published"


class AutonomousTriageResult(BaseModel):
    issue_key: str
    action: Literal["add_public_comment", "route_only", "escalate"]
    decision: Literal["respond", "route", "escalate"]
    confidence: float
    comment_id: str
    labels_added: list[str]
    status: Literal["autonomously_published"] = "autonomously_published"


class AuditEvent(BaseModel):
    id: int
    created_at: str
    issue_key: str
    event_type: str
    action: str
    category: str
    assigned_team_id: str
    assigned_team_name: str
    comment_id: str | None
    labels: list[str]


class LearnedKnowledgeArticle(BaseModel):
    article_id: str
    title: str
    category: str
    system_id: str
    status: Literal["Published"]
    last_reviewed: str
    owner: str
    resolution_summary: str
    tags: str
    source_issue_key: str
    source_comment_id: str
    verified_by: str


class KnowledgeCandidatePreview(BaseModel):
    issue_key: str
    source_comment_id: str
    verified_by: str
    title: str
    category: str
    system_id: str | None
    owner: str
    resolution_summary: str
    tags: list[str]
    will_write: bool = False


class LearnConfirmation(BaseModel):
    confirm: Literal["LEARN"]


class LearningRunConfirmation(BaseModel):
    confirm: Literal["RUN_LEARNING"]
