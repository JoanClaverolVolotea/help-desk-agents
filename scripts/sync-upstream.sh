#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Sync `src/` and `docs/` from an upstream repository into the current repo.

Usage:
  scripts/sync-upstream.sh [options]

Options:
  --remote <name>       Upstream remote name. Default: upstream
  --ref <branch>        Upstream branch or ref. Default: main
  --url <repo-url>      Remote URL used when the remote does not exist.
                        Default: https://github.com/openai/openai-agents-python.git
  --commit              Create a commit when sync changes are detected.
  --allow-dirty         Allow existing local changes under src/ or docs/.
  -h, --help            Show this help.

Examples:
  scripts/sync-upstream.sh
  scripts/sync-upstream.sh --ref main --commit
EOF
}

REMOTE_NAME="${UPSTREAM_REMOTE:-upstream}"
UPSTREAM_REF="${UPSTREAM_REF:-main}"
UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/openai/openai-agents-python.git}"
AUTO_COMMIT=0
ALLOW_DIRTY=0
SYNC_PATHS=("src" "docs")

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE_NAME="$2"
      shift 2
      ;;
    --ref)
      UPSTREAM_REF="$2"
      shift 2
      ;;
    --url)
      UPSTREAM_URL="$2"
      shift 2
      ;;
    --commit)
      AUTO_COMMIT=1
      shift
      ;;
    --allow-dirty)
      ALLOW_DIRTY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  echo "git is required." >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "This command must run inside a git repository." >&2
  exit 1
fi
cd "$REPO_ROOT"

if ! git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  git remote add "$REMOTE_NAME" "$UPSTREAM_URL"
  echo "Added remote '$REMOTE_NAME' -> $UPSTREAM_URL"
fi

if [[ "$ALLOW_DIRTY" -ne 1 ]]; then
  if ! git diff --quiet -- "${SYNC_PATHS[@]}" || ! git diff --cached --quiet -- "${SYNC_PATHS[@]}"; then
    echo "Local changes detected under src/ or docs/." >&2
    echo "Commit/stash them first, or run with --allow-dirty." >&2
    exit 1
  fi
  if git ls-files --others --exclude-standard -- "${SYNC_PATHS[@]}" | grep -q '.'; then
    echo "Untracked files detected under src/ or docs/." >&2
    echo "Commit/stash them first, or run with --allow-dirty." >&2
    exit 1
  fi
fi

git fetch --prune "$REMOTE_NAME" "$UPSTREAM_REF"
git restore --source "$REMOTE_NAME/$UPSTREAM_REF" --staged --worktree -- "${SYNC_PATHS[@]}"

if git diff --quiet -- "${SYNC_PATHS[@]}" && git diff --cached --quiet -- "${SYNC_PATHS[@]}"; then
  echo "No updates needed. src/ and docs/ already match $REMOTE_NAME/$UPSTREAM_REF."
  exit 0
fi

echo "Synced paths from $REMOTE_NAME/$UPSTREAM_REF:"
git status --short -- "${SYNC_PATHS[@]}"

if [[ "$AUTO_COMMIT" -eq 1 ]]; then
  git add "${SYNC_PATHS[@]}"
  git commit -m "Sync src and docs from $REMOTE_NAME/$UPSTREAM_REF"
  echo "Created commit for upstream sync."
else
  echo "Review changes, then commit when ready."
fi
