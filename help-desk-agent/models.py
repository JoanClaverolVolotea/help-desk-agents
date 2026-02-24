from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CaseCategory(str, Enum):
    ACCESS_RESET = "access_reset"
    ONBOARD_EMPLOYEE = "onboard_employee"


class HelpDeskCase(BaseModel):
    ticket_id: str
    jira_url: str
    title: str
    requester_name: str | None = None
    activity_type: str
    portal_group: str
    solution_type: str
    category: CaseCategory
    keywords: list[str] = Field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = [
            f"ticket_id={self.ticket_id}",
            f"title={self.title}",
            f"jira_url={self.jira_url}",
            f"activity_type={self.activity_type}",
            f"portal_group={self.portal_group}",
            f"solution_type={self.solution_type}",
            f"routing_category={self.category.value}",
        ]
        if self.requester_name:
            lines.append(f"requester_name={self.requester_name}")
        return lines
