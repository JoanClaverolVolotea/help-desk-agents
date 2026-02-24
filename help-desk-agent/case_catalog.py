from __future__ import annotations

from models import CaseCategory, HelpDeskCase

KNOWN_CASES: dict[str, HelpDeskCase] = {
    "USDV-176285": HelpDeskCase(
        ticket_id="USDV-176285",
        jira_url="https://volotea.atlassian.net/browse/USDV-176285",
        title="Francois Emeriau - Log in problem into eCrew",
        requester_name="Francois Emeriau",
        activity_type="Service request",
        portal_group="Login ans accounts",
        solution_type="Fix an account issue",
        category=CaseCategory.ACCESS_RESET,
        keywords=[
            "reset de acceso ecrew",
            "log in problem into ecrew",
            "fix an account issue",
            "francois emeriau",
            "ecrew",
            "account issue",
            "acceso",
            "reset de acceso",
        ],
    ),
    "USDV-176893": HelpDeskCase(
        ticket_id="USDV-176893",
        jira_url="https://volotea.atlassian.net/browse/USDV-176893",
        title="ALTAS E-MAIL/EFOS/PELESYS 16-02-2026",
        activity_type="Service request",
        portal_group="Login ans accounts",
        solution_type="Onboard new employee",
        category=CaseCategory.ONBOARD_EMPLOYEE,
        keywords=[
            "altas e-mail/efos/pelesys",
            "onboard new employee",
            "alta",
            "altas",
            "new employee",
            "efos",
            "pelesys",
            "e-mail",
            "email",
            "onboarding",
        ],
    ),
}


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("\n", " ").split())


def get_case_by_ticket_id(ticket_id: str) -> HelpDeskCase | None:
    normalized_ticket_id = ticket_id.strip().upper()
    return KNOWN_CASES.get(normalized_ticket_id)


def detect_case_from_text(ticket_text: str) -> HelpDeskCase | None:
    if not ticket_text.strip():
        return None

    upper_text = ticket_text.upper()
    for ticket_id, help_desk_case in KNOWN_CASES.items():
        if ticket_id in upper_text:
            return help_desk_case

    normalized_text = _normalize_text(ticket_text)
    case_scores = {
        ticket_id: sum(1 for keyword in help_desk_case.keywords if keyword in normalized_text)
        for ticket_id, help_desk_case in KNOWN_CASES.items()
    }
    best_ticket_id, best_score = max(case_scores.items(), key=lambda item: item[1])

    if best_score == 0:
        return None
    if list(case_scores.values()).count(best_score) > 1:
        return None

    return KNOWN_CASES[best_ticket_id]


def format_case_summary(help_desk_case: HelpDeskCase) -> str:
    return "\n".join(help_desk_case.summary_lines())
