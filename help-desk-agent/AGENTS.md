# Help Desk Agent Contributor Guide

## Purpose

This workspace exists to develop and iterate on a Help Desk Agent MVP using the OpenAI Agents SDK for Python.

Reference upstream project:
- https://github.com/openai/openai-agents-python

The goal is to learn and apply best practices for building production-ready agents while keeping this MVP focused and practical.

## Scope Rules (Strict)

- Only modify files inside `help-desk-agent/`.
- Never create, edit, delete, or refactor files outside `help-desk-agent/`.
- If a task would require changes outside `help-desk-agent/`, stop and report that constraint.

## Upstream Context Sync Policy

To keep implementation context current with the official OpenAI Agents SDK:

- Pull from the official upstream repository regularly.
- Minimum cadence: sync before starting new feature work and at least once per week.
- Use upstream updates for reference and alignment only; local development changes remain confined to `help-desk-agent/`.

## Working Objective

Within `help-desk-agent/`, continuously improve the MVP by:

- Building and refining agent behavior, tools, workflows, and API integration.
- Validating patterns against upstream SDK evolution.
- Documenting decisions that improve correctness, maintainability, and agent quality.

## Non-Goals

- General repository-wide refactors.
- Changes to core SDK files outside `help-desk-agent/`.
- Any edits unrelated to the Help Desk Agent MVP.
