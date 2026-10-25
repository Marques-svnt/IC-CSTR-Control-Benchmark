"""Checks the numbers of the JPC v6 manuscript against the CSV mirrors.

1. Main text: every quoted result must be a macro of `generated/numbers.tex`. The script
   regenerates the macros and fails if the committed file differs (stale numbers), then lists
   the literal numbers left in the prose of the main text so that each one can be classified as
   a protocol or model constant.
2. Supplementary material (text moved verbatim from v5): every decimal number in the prose must
   appear in some cell of `results/jpc/*.csv`; misses are listed for manual review.

Usage:
    .venv/bin/python scripts/check_text_numbers.py
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "papers" / "01_journal_of_process_control"
NUMBER = re.compile(r"(?<![\w.\\{])[-+]?\d+(?:\.\d+)?(?![\w}])")


def prose(text: str) -> str:
    """Text without comments, floats, displayed math, labels, refs, cites and macro names."""
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = re.sub(
        r"\\begin\{(table\*?|figure\*?|algorithm|equation\*?|align\*?|gather\*?)\}.*?"
        r"\\end\{\1\}",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(r"\\(label|ref|eqref|cite|input|includegraphics|url)\{[^}]*\}", "", text)
    text = re.sub(r"\\[A-Za-z]+", "", text)
    return text


def csv_values() -> set[str]:
    """Every numeric token of every CSV mirror, with and without a leading sign."""
    vals: set[str] = set()
    for f in (ROOT / "results" / "jpc").glob("*.csv"):
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.reader(fh):
                for cell in row:
                    for tok in re.findall(r"[-+]?\d+(?:\.\d+)?", cell):
                        vals |= {tok, tok.lstrip("+-")}
    return vals


def main() -> int:
    """Runs both checks; returns the number of hard failures."""
    failures = 0
    committed = (PAPER / "generated" / "numbers.tex").read_text(encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "jpc_v6_numbers.py")],
        check=True,
        capture_output=True,
    )
    if (PAPER / "generated" / "numbers.tex").read_text(encoding="utf-8") != committed:
        print(
            "ERROR: generated/numbers.tex was stale; it has been regenerated, recompile and commit"
        )
        failures += 1
    else:
        print("macros: generated/numbers.tex reproduces from the CSV mirrors")

    main_tex = (PAPER / "main.tex").read_text(encoding="utf-8")
    abstract = main_tex[main_tex.index("\\begin{abstract}") : main_tex.index("\\end{abstract}")]
    parts = {"abstract": abstract} | {
        p.name: p.read_text(encoding="utf-8") for p in sorted((PAPER / "sections").glob("*.tex"))
    }
    print("\nLiteral numbers left in the main-text prose (protocol or model constants):")
    for name, text in parts.items():
        lits = sorted(set(NUMBER.findall(prose(text))), key=lambda x: float(x))
        print(f"  {name}: {' '.join(lits) if lits else '-'}")

    vals = csv_values()
    supp = prose((PAPER / "supplementary.tex").read_text(encoding="utf-8"))
    decimals = sorted({t for t in NUMBER.findall(supp) if "." in t}, key=lambda x: float(x))
    nums = [float(v) for v in vals]

    def found(t: str) -> bool:
        """Exact token, or a CSV value that rounds to `t` at its number of decimals."""
        if t.lstrip("+-") in vals:
            return True
        half = 0.5 * 10 ** -len(t.split(".")[1])
        return any(abs(abs(float(t)) - v) <= half for v in nums)

    misses = [t for t in decimals if not found(t)]
    print(f"\nSupplement: {len(decimals)} decimal numbers in prose, {len(misses)} not in any CSV:")
    print("  " + " ".join(misses))
    return failures


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
