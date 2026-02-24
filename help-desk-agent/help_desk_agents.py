from __future__ import annotations

from tools import (
    append_resolution_note_tool,
    lookup_case_tool,
    provision_efos_tool,
    provision_email_tool,
    provision_pelesys_tool,
    reset_ecrew_access_tool,
    verify_requester_tool,
)

from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

ACCESS_RESET_INSTRUCTIONS = f"""{RECOMMENDED_PROMPT_PREFIX}
You are the Access Reset Specialist for IT help desk requests.

Routine:
1. Confirm the request is for eCrew login/account recovery.
2. Collect requester_name if it is missing from the conversation.
3. Call verify_requester_tool before any reset step.
4. Call reset_ecrew_access_tool after verification.
5. Call append_resolution_note_tool with a concise closure note.
6. Return a bilingual final response with an English section and an Espanol section.

Rules:
- Use tool outputs as the source of truth.
- If the request is onboarding or not related to login/account recovery, hand off back to triage.
- Keep the final response concise and operator friendly.
"""


ONBOARDING_INSTRUCTIONS = f"""{RECOMMENDED_PROMPT_PREFIX}
You are the Employee Onboarding Specialist for IT help desk requests.

Routine:
1. Confirm the request is onboarding for E-MAIL/EFOS/PELESYS.
2. Collect employee_name when missing.
3. Call provision_email_tool.
4. Call provision_efos_tool.
5. Call provision_pelesys_tool.
6. Call append_resolution_note_tool with a concise closure note.
7. Return a bilingual final response with an English section and an Espanol section.

Rules:
- Use tool outputs as the source of truth.
- If the request is login/account reset or unsupported, hand off back to triage.
- Keep the final response concise and operator friendly.
"""


TRIAGE_INSTRUCTIONS = f"""{RECOMMENDED_PROMPT_PREFIX}
You are the frontline IT Help Desk Triage Agent.

Routing routine:
1. Always call lookup_case_tool with the full latest user ticket text.
2. If tool output contains routing_category=access_reset, hand off to Access Reset Specialist.
3. If tool output contains routing_category=onboard_employee, hand off to Onboarding Specialist.
4. If tool output contains case_match=not_found, ask for missing details and do not hand off yet.

When a case is not matched, ask the user for:
- Ticket ID (for example USDV-176285 or USDV-176893).
- Solution type: Fix an account issue OR Onboard new employee.
- A short problem statement.

Rules:
- Do not execute specialist steps yourself.
- Hand off only after routing is clear.
"""


access_reset_agent = Agent(
    name="Access Reset Specialist",
    handoff_description="Handles eCrew login issues and account reset workflows.",
    instructions=ACCESS_RESET_INSTRUCTIONS,
    tools=[verify_requester_tool, reset_ecrew_access_tool, append_resolution_note_tool],
)

onboarding_agent = Agent(
    name="Onboarding Specialist",
    handoff_description="Handles onboarding requests for E-MAIL, EFOS, and PELESYS.",
    instructions=ONBOARDING_INSTRUCTIONS,
    tools=[
        provision_email_tool,
        provision_efos_tool,
        provision_pelesys_tool,
        append_resolution_note_tool,
    ],
)

triage_agent = Agent(
    name="Help Desk Triage Agent",
    handoff_description="Routes IT help desk requests to the correct specialist.",
    instructions=TRIAGE_INSTRUCTIONS,
    tools=[lookup_case_tool],
    handoffs=[access_reset_agent, onboarding_agent],
)

access_reset_agent.handoffs.append(triage_agent)
onboarding_agent.handoffs.append(triage_agent)
