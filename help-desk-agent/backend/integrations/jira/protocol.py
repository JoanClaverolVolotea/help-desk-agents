from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class JiraAttachment(BaseModel):
    attachment_id: str
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None
    download_url: str | None = None


class JiraComment(BaseModel):
    comment_id: str
    issue_key: str
    body: str
    author_account_id: str | None = None
    created_at: str | None = None


class JiraIssue(BaseModel):
    issue_key: str
    issue_id: str | None = None
    project_key: str
    issue_type: str
    summary: str
    description: str | None = None
    status: str
    reporter_email: str | None = None
    assignee_account_id: str | None = None
    resolver_group: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class JiraClient(Protocol):
    def search_issues(self, jql: str, fields: list[str] | None = None) -> list[JiraIssue]:
        """Search Jira issues using JQL."""

    def create_issue(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        description: str,
        fields: dict[str, Any] | None = None,
    ) -> JiraIssue:
        """Create a Jira issue and return the created issue."""

    def update_issue(self, issue_key: str, fields: dict[str, Any]) -> JiraIssue:
        """Update Jira issue fields and return the updated issue."""

    def add_comment(self, issue_key: str, body: str) -> JiraComment:
        """Append a comment to a Jira issue."""

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """Transition a Jira issue to a new workflow status."""

    def get_attachments(self, issue_key: str) -> list[JiraAttachment]:
        """Fetch issue attachments metadata for a Jira issue."""

    def get_issue(self, issue_key: str) -> JiraIssue:
        """Fetch a single Jira issue by key."""
