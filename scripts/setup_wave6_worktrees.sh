#!/usr/bin/env bash
# ==============================================================================
# Setup Git Worktrees for Wave 6 Remediation (Claude Code Concurrent Workflow)
# ==============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(dirname "$REPO_ROOT")"
VENV_DIR="$REPO_ROOT/.venv"

echo "=== Initializing Wave 6 Worktrees for Claude Code ==="
echo "Base repository: $REPO_ROOT"
echo "Target parent:   $PARENT_DIR"

# 1. Branch 1: Paper 1 (JPC)
WORKTREE_P1="$PARENT_DIR/IC-paper1-jpc"
BRANCH_P1="fix/paper1-jpc-remediation"
if [ ! -d "$WORKTREE_P1" ]; then
    echo "Creating worktree for Paper 1 (JPC) at: $WORKTREE_P1"
    git -C "$REPO_ROOT" worktree add -b "$BRANCH_P1" "$WORKTREE_P1" main
    ln -sf "$VENV_DIR" "$WORKTREE_P1/.venv"
else
    echo "Worktree $WORKTREE_P1 already exists."
fi

# 2. Branch 2: Paper 2 (CCE)
WORKTREE_P2="$PARENT_DIR/IC-paper2-cce"
BRANCH_P2="fix/paper2-cce-remediation"
if [ ! -d "$WORKTREE_P2" ]; then
    echo "Creating worktree for Paper 2 (CCE) at: $WORKTREE_P2"
    git -C "$REPO_ROOT" worktree add -b "$BRANCH_P2" "$WORKTREE_P2" main
    ln -sf "$VENV_DIR" "$WORKTREE_P2/.venv"
else
    echo "Worktree $WORKTREE_P2 already exists."
fi

# 3. Branch 3: Paper 3 (CERD)
WORKTREE_P3="$PARENT_DIR/IC-paper3-cerd"
BRANCH_P3="fix/paper3-cerd-remediation"
if [ ! -d "$WORKTREE_P3" ]; then
    echo "Creating worktree for Paper 3 (CERD) at: $WORKTREE_P3"
    git -C "$REPO_ROOT" worktree add -b "$BRANCH_P3" "$WORKTREE_P3" main
    ln -sf "$VENV_DIR" "$WORKTREE_P3/.venv"
else
    echo "Worktree $WORKTREE_P3 already exists."
fi

echo ""
echo "=== Worktrees Ready! ==="
echo "1. Paper 1 (JPC):  $WORKTREE_P1 (Branch: $BRANCH_P1)"
echo "2. Paper 2 (CCE):  $WORKTREE_P2 (Branch: $BRANCH_P2)"
echo "3. Paper 3 (CERD): $WORKTREE_P3 (Branch: $BRANCH_P3)"
echo "4. Main Hub:       $REPO_ROOT (Branch: main)"
