#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "This command must run inside the repository." >&2
  exit 1
fi

"$repo_root/scripts/sync-upstream.sh" "$@"
