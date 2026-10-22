# scripts/

Helper scripts for project maintenance. Not part of the research source code.

## github/

| Script | Purpose |
|---|---|
| `sync_to_github.ps1` | Push project files to GitHub via REST API (no git CLI needed). Usage: `.\scripts\github\sync_to_github.ps1 -Message "your message"` |

## overleaf/

| Script | Purpose |
|---|---|
| `overleaf_push.ps1` | Upload LaTeX sources to Overleaf project. |
| `overleaf_pull.ps1` | Download current Overleaf project files locally. |
| `overleaf_setup.ps1` | One-time configuration of Overleaf credentials. |
| `overleaf_sync.py` | Python helper called by the PS1 scripts. |
| `.olauth` | Overleaf auth token (not committed to git). |
