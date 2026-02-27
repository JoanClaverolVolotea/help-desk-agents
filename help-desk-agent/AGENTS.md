# Help Desk Agent Rules

This project folder is based on the OpenAI Agents Python repository:
`https://github.com/openai/openai-agents-python`.

## Goal

Build and maintain the Help Desk Agent application contained in this folder.

Every model task should help the user understand how to use agents while building a help desk agent.

## Scope (Hard Boundary)

- Read access can include surrounding repository context when needed.
- Write access is restricted to files under `help-desk-agent/` only.
- Do not modify, move, or delete files outside `help-desk-agent/`.
- If a request requires edits outside this folder, stop and ask the user to confirm a scope exception first.

## Working Guidance

- Keep implementation and explanations grounded in practical Help Desk Agent workflows.
- Prefer changes that clarify agent usage patterns (agents, runners, tools, handoffs, guardrails, streaming, and testing).
- Keep docs and examples focused on helping the user learn and operate this Help Desk Agent project.
