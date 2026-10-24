#!/usr/bin/env bash
# ==============================================================================
# Teardown Git Worktrees for Wave 6 after Merge
# ==============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(dirname "$REPO_ROOT")"

echo "=== Tearing Down Wave 6 Worktrees ==="

for p in "IC-paper1-jpc" "IC-paper2-cce" "IC-paper3-cerd"; do
    TARGET="$PARENT_DIR/$p"
    if [ -d "$TARGET" ]; then
        echo "Removing worktree: $TARGET"
        git -C "$REPO_ROOT" worktree remove "$TARGET" --force || rm -rf "$TARGET"
    fi
done

git -C "$REPO_ROOT" worktree prune
echo "=== Worktrees removed and pruned successfully. ==="
