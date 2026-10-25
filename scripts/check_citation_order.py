"""Checks that references are numbered in the order of first citation and that every key exists.

Reads the `.aux` written by LaTeX (citations are written at shipout, i.e. in page order) and the
`.bib` file. Exits with status 1 if a reference number appears before a smaller one, or if a
cited key is missing from the bibliography.

Usage:
    .venv/bin/python scripts/check_citation_order.py papers/01_journal_of_process_control/main.aux
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main(aux_path: Path) -> int:
    """Prints the first-citation order and returns the number of problems found."""
    aux = aux_path.read_text(encoding="utf-8", errors="replace")
    number = {k: int(n) for k, n in re.findall(r"\\bibcite\{([^}]+)\}\{\{(\d+)\}", aux)}
    order: list[str] = []
    for group in re.findall(r"\\citation\{([^}]+)\}", aux):
        for key in (k.strip() for k in group.split(",")):
            if key not in order:
                order.append(key)
    problems = [f"cited but not in bibliography: {k}" for k in order if k not in number]
    seq = [number[k] for k in order if k in number]
    problems += [
        f"[{n}] first cited after [{max(seq[:i])}]"
        for i, n in enumerate(seq)
        if i and n < max(seq[:i])
    ]
    if seq != list(range(1, len(seq) + 1)):
        problems.append(f"numbers are not 1..{len(seq)} in first-citation order: {seq}")
    print(f"{aux_path}: {len(seq)} references, first-citation order {seq}")
    for p in problems:
        print("ERROR:", p)
    return len(problems)


if __name__ == "__main__":
    sys.exit(1 if main(Path(sys.argv[1])) else 0)
