# Help Desk Agent Contributor Guide

## Purpose

This workspace exists to develop and iterate on a Help Desk Agent MVP using the OpenAI Agents SDK for Python.

Reference upstream project:
- https://github.com/openai/openai-agents-python

Reference package source of truth:
- https://pypi.org/project/openai-agents/

The goal is to learn and apply best practices for building production-ready agents while keeping this MVP focused and practical.

## Scope Rules (Strict)

- Only modify files inside `help-desk-agent/`.
- Never create, edit, delete, or refactor files outside `help-desk-agent/`.
- If a task would require changes outside `help-desk-agent/`, stop and report that constraint.

## Upstream Context Sync Policy

To keep implementation context current with the official OpenAI Agents SDK:

- Canonical upstream repository is `openai/openai-agents-python`.
- Pull from upstream regularly.
- Minimum cadence: sync before starting new feature work and at least once per week.
- Review upstream release notes, docs updates, examples, and migration-impacting changes.
- Use upstream updates for reference and alignment only; local development changes remain confined to `help-desk-agent/`.

## Dependency Update Policy

When updating the SDK version used by this MVP:

- Prefer package-manager updates over container image assumptions.
- Use one of:
  - `uv add --upgrade openai-agents`
  - `pip install -U openai-agents`
- Verify the installed version against the latest published PyPI release.
- Do not rely on unofficial or unavailable public Docker images as the source of SDK version truth.

## Suggested Sync Workflow

Use this lightweight workflow when refreshing local context from upstream:

1. `git fetch upstream --tags`
2. Review upstream changes (recent tags/releases, docs, examples, and relevant runtime updates).
3. Update dependency if needed (`uv add --upgrade openai-agents` or `pip install -U openai-agents`).
4. Run relevant local checks/tests for the MVP.
5. Update local `help-desk-agent/` documentation to reflect behavior/setup changes.

## Documentation Sync Checklist

Before closing a task that depends on upstream behavior:

- Confirm whether upstream introduced API, tooling, or setup changes that affect this MVP.
- Update local docs and contributor notes under `help-desk-agent/` when those changes matter.
- Record notable design or implementation decisions that affect maintainability.

## Working Objective

Within `help-desk-agent/`, continuously improve the MVP by:

- Building and refining agent behavior, tools, workflows, and API integration.
- Validating patterns against upstream SDK evolution.
- Documenting decisions that improve correctness, maintainability, and agent quality.

## Non-Goals

- General repository-wide refactors.
- Changes to core SDK files outside `help-desk-agent/`.
- Any edits unrelated to the Help Desk Agent MVP.
