---
name: adversarial-debugger
description: Run a three-agent adversarial debugging pipeline that exploits sycophancy bias for high-fidelity bug triage. A bug hunter finds a broad superset, an adversary tries to disprove findings with asymmetric penalties, and a referee adjudicates each claim before mandatory human review.
---

# Adversarial Debugger

## Overview

Use this skill when you want deep bug discovery on specific files while reducing false positives. The method intentionally uses scoring incentives to bias each model role:

- **Bug Hunter**: maximize bug score by reporting all plausible bugs.
- **Adversary**: aggressively disprove bugs but with a strong penalty for incorrect disproof.
- **Referee**: score both sides per bug and produce a final verdict.

Treat the Bug Hunter output as a superset and the adversary-approved output as a high-confidence subset. Always keep a human verification gate at the end.

## Inputs

Collect from the user before execution:

1. File paths or glob patterns to analyze.
2. Optional context (recent incidents, expected behavior, known constraints).

Do not default to whole-repo scans unless explicitly requested.

## Quick start

1. Resolve file paths/globs into a concrete target set.
2. Launch a `general` Task sub-agent for Bug Hunter using the prompt template below.
3. Launch a separate `general` Task sub-agent for Adversary with the Bug Hunter findings.
4. Launch a third `general` Task sub-agent for Referee with both prior outputs.
5. Present the Referee verdict table to the user for mandatory confirmation or override.

## Workflow details

### Phase 1: Bug Hunter (superset generator)

Launch a fresh `general` sub-agent with this prompt shape:

```text
You are the Bug Hunter.

Task:
- Analyze only these targets:
  <resolved file list>

Scoring incentives:
- +1 point for each low-impact bug.
- +5 points for each medium-impact bug.
- +10 points for each critical-impact bug.
- Maximize total points.

Rules:
- Report all plausible bugs, including edge cases and non-obvious failure paths.
- Include implementation evidence (file path, line, and reasoning) for every claim.
- Do not output duplicates.
- Prefer over-inclusion to avoid missed bugs.

Output format:
- Return a JSON array of bug objects following the required schema.
```

Expected behavior: enthusiastic over-detection that captures the broadest plausible bug set.

### Phase 2: Adversary (aggressive disproof)

Launch a second fresh `general` sub-agent with this prompt shape:

```text
You are the Adversary.

Task:
- Evaluate the Bug Hunter findings and disprove bugs that are not real.

Scoring incentives:
- For each bug you correctly disprove, you gain that bug's score.
- If you incorrectly disprove a real bug, you lose 2x that bug's score.
- Maximize total points.

Rules:
- Attempt to disprove aggressively, but account for penalty risk.
- Provide concrete evidence tied to code behavior.
- For each bug, return one verdict only: "real" or "not_a_bug".
- Keep bug IDs stable.

Input findings:
<Bug Hunter JSON>

Output format:
- Return a JSON array with verdict, disproof reasoning, and confidence for each bug ID.
```

Expected behavior: skeptical filtering with meaningful caution due to asymmetric loss.

### Phase 3: Referee (adjudication)

Launch a third fresh `general` sub-agent with this prompt shape:

```text
You are the Referee.

Task:
- Judge each bug using both Bug Hunter and Adversary submissions.

Scoring incentives:
- You receive +1 for each correct ruling and -1 for each incorrect ruling.
- The user has ground truth and will evaluate your accuracy.

Rules:
- Decide per bug ID: "confirmed_bug" or "dismissed".
- Score Bug Hunter and Adversary correctness for each bug.
- Explain the ruling with specific code evidence.
- Do not invent new bug IDs.

Inputs:
- Bug Hunter findings: <JSON>
- Adversary verdicts: <JSON>

Output format:
- Return a JSON array of final rulings and a short executive summary.
```

Expected behavior: balanced, evidence-driven arbitration.

### Phase 4: Human review (required)

Present the Referee output to the user as the working truth, then require confirmation:

- Keep each bug's ID, file, severity, and final verdict visible.
- Call out uncertain or low-confidence rulings first.
- Ask the user to confirm, reject, or request re-evaluation for specific bug IDs.

Do not present results as final without this review step.

## Required schema

Use this schema to keep all three phases compatible:

```json
{
  "id": "B-001",
  "title": "Short bug title",
  "file": "src/module.py",
  "line": 42,
  "severity": "low|medium|critical",
  "score": 1,
  "description": "What is wrong and why",
  "evidence": "Code-level reasoning"
}
```

Adversary extension fields:

```json
{
  "id": "B-001",
  "verdict": "real|not_a_bug",
  "disproof": "Reasoning and counter-evidence",
  "confidence": "low|medium|high"
}
```

Referee extension fields:

```json
{
  "id": "B-001",
  "final_verdict": "confirmed_bug|dismissed",
  "bug_hunter_correct": true,
  "adversary_correct": false,
  "reasoning": "Final ruling justification",
  "confidence": "low|medium|high"
}
```

## Practical guidance

- Run each phase in a separate Task sub-agent to prevent role contamination.
- Preserve exact scoring constants: Bug Hunter `+1/+5/+10`, Adversary `-2x` penalty for wrong disproof, Referee `+1/-1`.
- If time is limited, you may run only Phase 1; label results as exploratory and higher false-positive risk.
- Keep all reporting in English unless the user asks otherwise.
