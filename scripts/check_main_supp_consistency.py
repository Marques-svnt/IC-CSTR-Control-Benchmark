r"""Checks that numbers shared by the JPC main text and the Supplementary Material are identical.

Main-text numbers are macros of generated/numbers.tex or condensed tables built from the CSV
mirrors; the supplement quotes some of the same values in its prose and in full tables. This
script compares, for the items listed below, the supplement against the CSV that the main text
uses, and exits with status 1 on any difference.

Usage:
    .venv/bin/python scripts/check_main_supp_consistency.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jpc_v6_numbers import PAPER, SHORT, SIX, cell, num, rows  # noqa: E402

FLOAT = r"[-+]?\d+(?:\.\d+)?"


def supp_list(text: str, lead: str, n: int) -> list[str]:
    """The first `n` numbers following the phrase `lead` of the supplement."""
    tail = text[text.index(lead) + len(lead):]
    return re.findall(FLOAT, tail)[:n]


def main() -> int:
    """Prints every compared item and returns the number of mismatches."""
    supp = (PAPER / "supplementary.tex").read_text(encoding="utf-8")
    bad = 0

    def same(item: str, got: list[str], want: list[str]) -> None:
        nonlocal bad
        ok = [float(g) for g in got] == [float(w) for w in want]
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {item}: supplement {got} / CSV {want}")

    tt = rows("antiwindup_tt_summary")
    for lead, col in (
        ("With $T_t^{\\mathrm{mm}}$ the worst ratio is", "mm"),
        ("$T_t = \\sqrt{T_iT_d}$ gives worst ratios of", "\\(\\sqrt{T_iT_d}\\)"),
        ("conditioning techniques \\cite{peng1996nonlinear},", "\\(T_i\\)"),
    ):
        same(f"T_t worst ratios ({col})", supp_list(supp, lead, 6), [r[col] for r in tt])

    cs = "\\(\\|CS\\|_\\infty\\) (L/min/K)"
    khf = [cell("exact_robustness_table", cs, Method=m) for m in SIX]
    got = supp_list(supp, "and equals it to within $0.3$~L/min/K for all six loops:", 6)
    order = ["Ziegler-Nichols", "Cohen-Coon", "Tyreus-Luyben", "AMIGO", SIX[5], "Skogestad SIMC"]
    same("K_hf = ||CS|| (S3 prose vs Table 3)", got, [khf[SIX.index(m)] for m in order])

    testbed = (PAPER / "tables" / "v7_testbed.tex").read_text(encoding="utf-8")
    for m in SIX:
        line = next(x for x in testbed.splitlines() if x.startswith(SHORT[m] + " &"))
        cells = [c.strip(" \\") for c in line.split("&")[1:]]
        bench = [cell("benchmark_table", k, Method=m) for k in (
            "\\(K_p\\)", "\\(T_i\\text{ (min)}\\)", "\\(T_d\\text{ (min)}\\)", "IAE", "TV (L/min)",
            "\\(M_p\\text{ (\\%)}\\)", "\\(M_s\\)")]
        exact = [cell("exact_robustness_table", k, Method=m)
                 for k in ("\\(\\|S\\|_\\infty\\) (lin.)", "\\(\\|CS\\|_\\infty\\) (L/min/K)")]
        same(f"Table 3 vs S1/S3 ({SHORT[m]})", cells, bench + exact)

    abl = {m: cell("antiwindup_ablation", c, Method=m) for m in ("Ziegler-Nichols", "Cohen-Coon")
           for c in ("Sign-blind amp.",)}
    none = {m: cell("antiwindup_ablation", "None", Method=m) for m in abl}
    got = supp_list(supp, "it is worse than no anti-windup (IAE", 4)
    same("sign-blind vs none (S3 prose vs Table 4)", got,
         [f"{num(abl[m]):.2f}" for m in abl] + [f"{num(none[m]):.2f}" for m in none])

    latch = rows("latch_check")
    got = supp_list(supp, "for ZN, $I^\\star =", 1)
    same("I* of ZN (S3 prose vs latch_check)", got, [f"{float(latch[0]['I_star']):.0f}"])
    got = supp_list(supp, "($T(t_f) - T_{sp} =", 1)
    same("latch offset (S3 prose vs latch_check)", got, [f"{float(latch[0]['Tf_minus_Tsp']):.2f}"])
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
