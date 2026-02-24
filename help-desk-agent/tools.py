from __future__ import annotations

from case_catalog import detect_case_from_text, format_case_summary, get_case_by_ticket_id
from models import CaseCategory, HelpDeskCase

from agents import function_tool

SUPPORTED_CASE_HINT = (
    "Supported solution types are 'Fix an account issue' and 'Onboard new employee'."
)


def _normalize_person_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _must_get_case(ticket_id: str) -> tuple[str, HelpDeskCase | None]:
    normalized_ticket_id = ticket_id.strip().upper()
    return normalized_ticket_id, get_case_by_ticket_id(normalized_ticket_id)


@function_tool(
    name_override="lookup_case_tool",
    description_override="Identify whether ticket text maps to access reset or onboarding.",
)
def lookup_case_tool(ticket_text: str) -> str:
    help_desk_case = detect_case_from_text(ticket_text)
    if help_desk_case is None:
        return (
            "case_match=not_found\n"
            "routing_category=unknown\n"
            "No known help desk case matched this ticket text. "
            f"{SUPPORTED_CASE_HINT}"
        )

    return f"case_match=found\n{format_case_summary(help_desk_case)}"


@function_tool
def verify_requester_tool(ticket_id: str, requester_name: str) -> str:
    normalized_ticket_id, help_desk_case = _must_get_case(ticket_id)
    if help_desk_case is None:
        return f"Requester verification failed: unknown ticket_id={normalized_ticket_id}."

    if help_desk_case.category != CaseCategory.ACCESS_RESET:
        return (
            f"Requester verification not required for ticket_id={normalized_ticket_id} "
            "because this case is not an access reset flow."
        )

    expected_name = help_desk_case.requester_name
    if expected_name and _normalize_person_name(expected_name) != _normalize_person_name(
        requester_name
    ):
        return (
            f"Requester verification warning for {normalized_ticket_id}: "
            f"expected requester '{expected_name}', got '{requester_name}'. "
            "Ask for confirmation before reset."
        )

    return (
        f"Requester identity verified for ticket_id={normalized_ticket_id} "
        f"with requester_name={requester_name}."
    )


@function_tool
def reset_ecrew_access_tool(ticket_id: str, requester_name: str) -> str:
    normalized_ticket_id, help_desk_case = _must_get_case(ticket_id)
    if help_desk_case is None:
        return f"Access reset failed: unknown ticket_id={normalized_ticket_id}."

    if help_desk_case.category != CaseCategory.ACCESS_RESET:
        return (
            f"Access reset blocked for ticket_id={normalized_ticket_id}: "
            "ticket category is not access_reset."
        )

    return (
        "eCrew reset executed for "
        f"ticket_id={normalized_ticket_id} and requester={requester_name}.\n"
        "Step 1: Account unlocked.\n"
        "Step 2: Password reset and temporary credential issued.\n"
        "Step 3: Active sessions revoked."
    )


@function_tool
def provision_email_tool(ticket_id: str, employee_name: str) -> str:
    normalized_ticket_id, help_desk_case = _must_get_case(ticket_id)
    if help_desk_case is None:
        return f"Email provisioning failed: unknown ticket_id={normalized_ticket_id}."
    if help_desk_case.category != CaseCategory.ONBOARD_EMPLOYEE:
        return (
            f"Email provisioning blocked for ticket_id={normalized_ticket_id}: "
            "ticket category is not onboard_employee."
        )

    username = employee_name.strip().lower().replace(" ", ".")
    return (
        f"Email provisioned for ticket_id={normalized_ticket_id}.\n"
        f"Mailbox={username}@volotea.example.\n"
        "Status=active."
    )


@function_tool
def provision_efos_tool(ticket_id: str, employee_name: str) -> str:
    normalized_ticket_id, help_desk_case = _must_get_case(ticket_id)
    if help_desk_case is None:
        return f"EFOS provisioning failed: unknown ticket_id={normalized_ticket_id}."
    if help_desk_case.category != CaseCategory.ONBOARD_EMPLOYEE:
        return (
            f"EFOS provisioning blocked for ticket_id={normalized_ticket_id}: "
            "ticket category is not onboard_employee."
        )

    return (
        f"EFOS access provisioned for ticket_id={normalized_ticket_id}.\n"
        f"Employee={employee_name}.\n"
        "Role=GroundOperations.Basic."
    )


@function_tool
def provision_pelesys_tool(ticket_id: str, employee_name: str) -> str:
    normalized_ticket_id, help_desk_case = _must_get_case(ticket_id)
    if help_desk_case is None:
        return f"PELESYS provisioning failed: unknown ticket_id={normalized_ticket_id}."
    if help_desk_case.category != CaseCategory.ONBOARD_EMPLOYEE:
        return (
            f"PELESYS provisioning blocked for ticket_id={normalized_ticket_id}: "
            "ticket category is not onboard_employee."
        )

    return (
        f"PELESYS training profile created for ticket_id={normalized_ticket_id}.\n"
        f"Employee={employee_name}.\n"
        "Curriculum=InitialCrewOnboarding."
    )


@function_tool
def append_resolution_note_tool(ticket_id: str, note: str) -> str:
    normalized_ticket_id, help_desk_case = _must_get_case(ticket_id)
    if help_desk_case is None:
        return f"Resolution note failed: unknown ticket_id={normalized_ticket_id}."

    cleaned_note = " ".join(note.split())
    return f"Resolution note saved for ticket_id={normalized_ticket_id}.\nNote={cleaned_note}"
