---
name: upstream-sync-openai
description: Sync src/ and docs/ from the official openai-agents-python upstream repository while keeping origin pointed at the private repository.
---

# Upstream Sync

## Overview

Use this skill when asked to keep local `src/` and `docs/` aligned with the official OpenAI Agents Python repository, without changing the private `origin` remote.

## Quick start

1. Run `bash .agents/skills/upstream-sync-openai/scripts/run.sh`.
2. Review the resulting `git status --short -- src docs`.
3. Commit the sync change when requested.

## Workflow

1. Ensure the repository has an `upstream` remote.
   - If it does not exist, the script adds:
     `https://github.com/openai/openai-agents-python.git`
2. Fetch `upstream/main` (or a custom ref).
3. Restore only `src/` and `docs/` from that upstream ref.
4. Keep `origin` untouched so push/pull continues to use the private repo.

## Options

Pass options through the wrapper:

- `--remote <name>`: Upstream remote name. Default: `upstream`.
- `--ref <branch>`: Upstream ref. Default: `main`.
- `--url <repo-url>`: URL to use if remote must be created.
- `--commit`: Auto-commit after sync.
- `--allow-dirty`: Allow existing local changes under `src/` and `docs/`.

Example:

```bash
bash .agents/skills/upstream-sync-openai/scripts/run.sh --ref main --commit
```

## Resources

### scripts/run.sh

Thin wrapper that executes `scripts/sync-upstream.sh` from the repository root.
