r"""Numbers and condensed tables of the JPC v7 manuscript, generated from the CSV mirrors.

Every value quoted in the main text of Artigo 1 is a LaTeX macro defined here from
`results/jpc/*.csv` (written by `experiments/build_paper_assets.py jpc-remediation`), or from
the plant code for the two steady-state quantities of Proposition 1. Nothing is typed by hand.

Outputs:
    papers/01_journal_of_process_control/generated/numbers.tex   (\\newcommand macros)
    papers/01_journal_of_process_control/tables/v7_*.tex         (condensed tables)
    results/jpc/v9_numbers.csv                                    (macro -> value, source)

Usage:
    .venv/bin/python scripts/jpc_v6_numbers.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RES = ROOT / "results" / "jpc"
PAPER = ROOT / "papers" / "01_journal_of_process_control"
ONE_DOF = ("Ziegler-Nichols", "Cohen-Coon", "Tyreus-Luyben", "AMIGO", "Skogestad SIMC")
OPT = "Optimal ITAE ($M_s^{\\mathrm{FOPTD}} \\leq 1.6$)"
SIX = (*ONE_DOF, OPT)
SHORT = {
    "Ziegler-Nichols": "ZN",
    "Cohen-Coon": "CC",
    "Tyreus-Luyben": "TL",
    "AMIGO": "AMIGO",
    "Skogestad SIMC": "SIMC",
    OPT: "Optimal ITAE",
}
RATE = "Amp.+rate direct. (Eq.~\\ref{eq:clamping_antiwindup})"
BC_SQRT, BC_CV = "BC ($\\sqrt{T_iT_d}$)", "BC ($T_t^{\\mathrm{cv}}$)"


def rows(stem: str) -> list[dict[str, str]]:
    """CSV mirror of one paper table, with blank group cells filled from the row above."""
    with open(RES / f"{stem}.csv", newline="", encoding="utf-8") as fh:
        out = list(csv.DictReader(fh))
    first = next(iter(out[0]))
    for prev, row in zip(out, out[1:]):
        if not row[first]:
            row[first] = prev[first]
    return out


def cell(stem: str, col: str, **match: str) -> str:
    """The single cell of `stem` in column `col` whose row matches every key=value in `match`."""
    hits = [r for r in rows(stem) if all(r[k] == v for k, v in match.items())]
    if len(hits) != 1:
        raise KeyError(f"{stem}: {match} matched {len(hits)} rows")
    return hits[0][col]


def num(text: str, part: int = 0) -> float:
    r"""Numeric part `part` of a cell such as '0.94 / 22.6' or '1.29 $\\pm$ 0.03'."""
    return float(re.findall(r"[-+]?\d+(?:\.\d+)?", text)[part])


MACROS: list[tuple[str, str, str]] = []


def define(name: str, value: float | str, source: str, fmt: str = "{:.2f}") -> None:
    r"""Registers macro \\v<name> with the formatted value and its provenance."""
    text = value if isinstance(value, str) else fmt.format(value)
    MACROS.append((name, text, source))


def booktabs(
    header: list[str], body: list[list[str]], caption: str, label: str, group: str = "",
    env: str = "table*",
) -> str:
    """Starred booktabs float in the style of exp02.export_latex_table; `group` is an optional top row."""
    top = [group + r" \\"] if group else []
    lines = top + [" & ".join(header) + r" \\", r"\midrule"] + [" & ".join(r) + r" \\" for r in body]
    return (
        f"\\begin{{{env}}}[t]\n\\centering\n\\footnotesize\n\\setlength{{\\tabcolsep}}{{3pt}}\n"
        f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
        f"\\begin{{tabular}}{{l{'c' * (len(header) - 1)}}}\n\\toprule\n"
        + "\n".join(lines)
        + f"\n\\bottomrule\n\\end{{tabular}}\n\\end{{{env}}}\n"
    )


def signblind_numbers() -> None:
    """Sign-blind latch location over S_max (smax_signblind_diagnostics)."""
    tab = rows("smax_signblind_diagnostics")
    low = [r for r in tab if float(r["t_lower_min"]) > float(r["t_upper_min"])]
    if [(r["Method"], float(r["S_max"])) for r in low] != [("Ziegler-Nichols", 240.0)]:
        raise ValueError(f"text names ZN at 240 as the only lower-stop latch: {low}")
    r = low[0]
    define("sbZNlowtime", float(r["t_lower_min"]), "smax_signblind_diagnostics", "{:.2f}")
    define("sbZNlowerr", float(r["final_error_K"]), "smax_signblind_diagnostics", "{:+.1f}")
    define("sbZNlowrate", float(r["error_rate_end_K_per_min"]), "smax_signblind_diagnostics", "{:.2f}")


def ablation_numbers() -> None:
    """Nominal-step ablation, latch mechanism, Proposition 1 and the scenarios table."""
    for name in ("Ziegler-Nichols", "Cohen-Coon"):
        s = SHORT[name]
        for col, tag in (
            ("None", "none"),
            (BC_SQRT, "bc"),
            (BC_CV, "bccv"),
            ("Sign-blind amp.", "sign"),
            ("Amp. direct.", "amp"),
            ("Amp.+rate uncond.", "rateunc"),
            (RATE, "dir"),
        ):
            define(
                f"{s}{tag}",
                num(cell("antiwindup_ablation", col, Method=name)),
                "antiwindup_ablation",
            )
        define(
            f"{s}signMp",
            num(cell("antiwindup_ablation", "Sign-blind amp.", Method=name), 1),
            "antiwindup_ablation",
            "{:.1f}",
        )
        mech = {"Method": name, "Anti-windup": "Sign-blind amp."}
        define(
            f"{s}atmax",
            num(cell("antiwindup_mechanism", "Time at \\(u_{\\max}\\) (min)", **mech)),
            "antiwindup_mechanism",
        )
        define(
            f"{s}discrep",
            num(
                cell(
                    "antiwindup_mechanism",
                    "\\(\\max|u_{\\mathrm{raw}}-u_{\\mathrm{act}}|\\) (L/min)",
                    **mech,
                )
            ),
            "antiwindup_mechanism",
            "{:.0f}",
        )
    define(
        "latcherr",
        num(
            cell(
                "antiwindup_mechanism",
                "\\(T(t_f)-T_{sp}\\) (K)",
                Method="Ziegler-Nichols",
                **{"Anti-windup": "Sign-blind amp."},
            )
        ),
        "antiwindup_mechanism",
        "{:+.2f}",
    )
    define(
        "latchgap",
        abs(
            num(
                cell(
                    "antiwindup_mechanism",
                    "\\(T(t_f)-T_{sp}\\) (K)",
                    Method="Ziegler-Nichols",
                    **{"Anti-windup": "Sign-blind amp."},
                )
            )
        ),
        "antiwindup_mechanism (|T(t_f) - T_sp|)",
    )
    define(
        "latchTmin",
        num(
            cell(
                "antiwindup_mechanism",
                "\\(T_{\\min}\\) (K)",
                Method="Ziegler-Nichols",
                **{"Anti-windup": "Sign-blind amp."},
            )
        ),
        "antiwindup_mechanism",
        "{:.1f}",
    )
    define(
        "ZNnominal",
        num(cell("benchmark_table", "IAE", Method="Ziegler-Nichols")),
        "benchmark_table",
        "{:.3f}",
    )

    amp, rate = [], []
    for scen in ("$-5$ K step", "$+5$ K step"):
        for name in ("Ziegler-Nichols", "Cohen-Coon", "AMIGO", OPT):
            r = {"Scenario": scen, "Method": name}
            amp.append(num(cell("antiwindup_scenarios", "Amp. direct.", **r)))
            rate.append(num(cell("antiwindup_scenarios", RATE, **r)))
    define("scenampmin", min(amp), "antiwindup_scenarios")
    define("scenampmax", max(amp), "antiwindup_scenarios")
    define("scendirmin", min(rate), "antiwindup_scenarios")
    define("scendirmax", max(rate), "antiwindup_scenarios")
    for scen, tag in (("$-5$ K step", "five"), ("Load (deterministic)", "load")):
        for name in ("Ziegler-Nichols", "Cohen-Coon"):
            r = {"Scenario": scen, "Method": name}
            define(
                f"{SHORT[name]}{tag}sign",
                num(cell("antiwindup_scenarios", "Sign-blind amp.", **r)),
                "antiwindup_scenarios",
            )
            define(
                f"{SHORT[name]}{tag}none",
                num(cell("antiwindup_scenarios", "None", **r)),
                "antiwindup_scenarios",
            )


def proposition_numbers() -> None:
    """T_inf and I* of Proposition 1 from the plant model and the benchmark gains."""
    from src.sim_core.cstr_plant import CSTRPlant

    plant = CSTRPlant()
    t_sp = plant.find_steady_state(q_j=100.0).T - 2.0
    t_inf = plant.find_steady_state(q_j=300.0).T
    define("Tinf", t_inf, "CSTRPlant.find_steady_state(q_j=300)")
    for name in ("Ziegler-Nichols", "Cohen-Coon"):
        kp = abs(num(cell("benchmark_table", "\\(K_p\\)", Method=name)))
        define(
            f"{SHORT[name]}Istar",
            300.0 - 100.0 + kp * (t_sp - t_inf),
            "u_max - u_bias + |Kp|(T_sp - T_inf); Kp from benchmark_table",
            "{:.0f}",
        )


def latch_check_numbers() -> None:
    """Hypotheses of Proposition 1 checked on the simulated latch (latch_check.csv)."""
    for r in rows("latch_check"):
        flags = ("I_frozen_after_k0", "u_raw_ge_umax_after_k0", "e_pos_after_k0")
        if not all(r[f] == "True" for f in flags) or float(r["margin_band"]) <= 0.0:
            raise ValueError(f"Proposition 1 hypotheses fail on the simulated latch: {r}")
        s = SHORT[r["Method"]]
        define(f"{s}tkzero", float(r["t_k0_min"]), "latch_check", "{:.2f}")
        define(f"{s}Ikzero", float(r["I_k0"]), "latch_check", "{:.0f}")
        define(f"{s}Dbar", float(r["D_bar_band"]), "latch_check (D bound from Eq. 10 and the band)", "{:.0f}")
        define(f"{s}delta", float(r["delta_K"]), "latch_check", "{:.2f}")
        define(f"{s}latchmargin", float(r["margin_band"]), "latch_check", "{:.0f}")
        istar = next(v for n, v, _ in MACROS if n == f"{s}Istar")
        if istar != f"{float(r['I_star']):.0f}":
            raise ValueError(f"I* of latch_check ({r['I_star']}) differs from Proposition 1 ({istar})")


def back_calculation_numbers() -> None:
    """One T_t per loop (Table antiwindup_tt_summary)."""
    tab = rows("antiwindup_tt_summary")
    cols = {
        "mm": "mm",
        "sqrt": "\\(\\sqrt{T_iT_d}\\)",
        "ti": "\\(T_i\\)",
        "cv": "cv: \\(\\pm 5\\)~K",
    }
    for tag, col in cols.items():
        vals = [num(r[col]) for r in tab]
        define(f"tt{tag}max", max(vals), "antiwindup_tt_summary")
        define(f"tt{tag}min", min(vals), "antiwindup_tt_summary")
        define(f"tt{tag}maxpct", 100.0 * (max(vals) - 1.0), "antiwindup_tt_summary", "{:.0f}")
        define(f"tt{tag}minpct", 100.0 * (1.0 - min(vals)), "antiwindup_tt_summary", "{:.0f}")


def back_calculation_detail() -> None:
    """Unrestricted design-step choice and the TV/overshoot comparison at T_t^cv."""
    tab = rows("antiwindup_tt_summary")
    out = [SHORT[r["Method"]] for r in tab if r["in range"] == "no"]
    define("ttoutside", ", ".join(out[:-1]) + " and " + out[-1] if len(out) > 1 else out[0],
           "antiwindup_tt_summary (unrestricted T_t^cv outside [T_d, T_i])")
    col_r, col_f = "cv: \\(\\pm 5\\)~K", "free: \\(\\pm 5\\)~K"
    gain = [num(r[col_r]) - num(r[col_f]) for r in tab if r["in range"] == "no"]
    define("ttfreemaxgain", max(gain), "antiwindup_tt_summary (largest drop of the +-5 K worst ratio when leaving the range)")
    define("ttfreemaxloss", -min(gain), "antiwindup_tt_summary (largest rise of the +-5 K worst ratio when leaving the range)")
    lower, upper = [], []
    for r in tab:
        td, ti = (float(x) for x in r["\\([T_d, T_i]\\)"].strip("[]").split(","))
        cv = float(r["\\(T_t^{\\mathrm{cv}}\\)"])
        lower += [SHORT[r["Method"]]] if cv == td else []
        upper += [SHORT[r["Method"]]] if cv == ti else []
    join = lambda xs: " and ".join(xs) if len(xs) < 3 else ", ".join(xs[:-1]) + " and " + xs[-1]  # noqa: E731
    define("ttcvlower", join(lower), "antiwindup_tt_summary (T_t^cv = T_d)")
    define("ttcvupper", join(upper), "antiwindup_tt_summary (T_t^cv = T_i)")
    free = {SHORT[r["Method"]]: float(r["free \\(T_t^{\\mathrm{cv}}\\)"]) for r in tab}
    define("ttfreeZN", free["ZN"], "antiwindup_tt_summary", "{:.3f}")
    define("ttfreeCC", free["CC"], "antiwindup_tt_summary", "{:.3f}")
    simc = next(r for r in tab if r["Method"] == "Skogestad SIMC")
    ti_simc = float(simc["\\([T_d, T_i]\\)"].strip("[]").split(",")[1])
    freex = {SHORT[r["Method"]]: float(r["free, exact"]) for r in tab}
    define("ttfreexZN", freex["ZN"], "antiwindup_tt_summary (free choice, exact factor)", "{:.3f}")
    define("ttfreexCC", freex["CC"], "antiwindup_tt_summary (free choice, exact factor)", "{:.3f}")
    dif = [(abs(num(r[c]) - num(r["cv: \\(\\pm 5\\)~K"])), SHORT[r["Method"]])
           for r in tab for c in ("free: \\(\\pm 5\\)~K", "exact: \\(\\pm 5\\)~K")]
    top = max(dif)
    define("ttfreediffmax", top[0], "antiwindup_tt_summary (largest |free - cv| of the +-5 K worst ratio)")
    define("ttfreediffloop", top[1], "antiwindup_tt_summary")
    define("ttfreediffrest", max(d for d, n in dif if n != top[1]), "antiwindup_tt_summary (other loops)")
    define("ttfreexgain", max(num(r["cv: \\(\\pm 5\\)~K"]) - num(r["exact: \\(\\pm 5\\)~K"]) for r in tab),
           "antiwindup_tt_summary (largest drop of the +-5 K worst ratio, exact free choice vs T_t^cv)")
    define("ttfreeSIMCovTi", free["SIMC"] / ti_simc, "antiwindup_tt_summary (free T_t^cv / T_i)", "{:.0f}")
    for step, s in (("$-2$ K", "two"), ("$-5$ K", "m"), ("$+5$ K", "p")):
        m = {"Method": "Skogestad SIMC", "Step": step}
        define(f"SIMCcv{s}", num(cell("antiwindup_tt_sweep", "IAE $T_t^{\\mathrm{cv}}$", **m)), "antiwindup_tt_sweep")
        define(f"SIMCti{s}", num(cell("antiwindup_tt_sweep", "IAE $T_t=T_i$", **m)), "antiwindup_tt_sweep")
    tv = rows("antiwindup_tt_tvmp")
    emp = [r for r in tv if r["Method"] in ("Ziegler-Nichols", "Cohen-Coon")]
    define("empTVlower", f"{sum(num(r['TV BC (L/min)']) < num(r['TV dir. (L/min)']) for r in emp)}",
           "antiwindup_tt_tvmp (ZN and CC cases with lower TV under BC)")
    define("empMplower", f"{sum(num(r['\\(M_p\\) BC (\\%)']) < num(r['\\(M_p\\) dir. (\\%)']) for r in emp)}",
           "antiwindup_tt_tvmp (ZN and CC cases with lower overshoot under BC)")
    define("empcases", f"{len(emp)}", "antiwindup_tt_tvmp")
    cc5 = {"Method": "Cohen-Coon", "Step": "$+5$ K"}
    for col, tag in (("TV dir. (L/min)", "CCfiveTVdir"), ("TV BC (L/min)", "CCfiveTVbc"),
                     ("\\(M_p\\) dir. (\\%)", "CCfiveMpdir"), ("\\(M_p\\) BC (\\%)", "CCfiveMpbc")):
        define(tag, num(cell("antiwindup_tt_tvmp", col, **cc5)), "antiwindup_tt_tvmp", "{:.1f}")
    rest = [r for r in tv if r["Method"] in ("Tyreus-Luyben", "Skogestad SIMC", OPT)]
    mp = "\\(M_p\\) BC (\\%)", "\\(M_p\\) dir. (\\%)"
    define("restcases", f"{len(rest)}", "antiwindup_tt_tvmp (TL, SIMC, Optimal ITAE)")
    define("restTVhigher", f"{sum(num(r['TV BC (L/min)']) > num(r['TV dir. (L/min)']) for r in rest)}",
           "antiwindup_tt_tvmp (TL, SIMC, Optimal ITAE cases with higher TV under BC)")
    if any(num(r[mp[0]]) < num(r[mp[1]]) for r in rest):
        raise ValueError("text states that BC never overshoots less for TL, SIMC and Optimal ITAE")
    define("restMphigher", f"{sum(num(r[mp[0]]) > num(r[mp[1]]) for r in rest)}",
           "antiwindup_tt_tvmp (TL, SIMC, Optimal ITAE cases with higher overshoot under BC)")
    for m, step, col, tag in (
        ("Skogestad SIMC", "$-5$ K", "TV dir. (L/min)", "SIMCfiveTVdir"),
        ("Skogestad SIMC", "$-5$ K", "TV BC (L/min)", "SIMCfiveTVbc"),
        (OPT, "$+5$ K", mp[1], "OPTfiveMpdir"),
        (OPT, "$+5$ K", mp[0], "OPTfiveMpbc"),
        ("Tyreus-Luyben", "$+5$ K", mp[1], "TLfiveMpdir"),
        ("Tyreus-Luyben", "$+5$ K", mp[0], "TLfiveMpbc"),
    ):
        define(tag, num(cell("antiwindup_tt_tvmp", col, Method=m, Step=step)), "antiwindup_tt_tvmp", "{:.1f}")
    simc = [r for r in tv if r["Method"] == "Skogestad SIMC"]
    inc = [100.0 * (num(r["TV BC (L/min)"]) / num(r["TV dir. (L/min)"]) - 1.0) for r in simc]
    define("SIMCtvincmin", min(inc), "antiwindup_tt_tvmp", "{:.0f}")
    define("SIMCtvincmax", max(inc), "antiwindup_tt_tvmp", "{:.0f}")


def regime_map() -> list[list[str]]:
    """Ratio row of the S_max regime map for every loop; returns the condensed table body."""
    tab = rows("smax_regime_map")
    ratio = "$\\mathrm{IAE}_{\\mathrm{amp}}/\\mathrm{IAE}_{\\mathrm{rate}}$"
    sign = "Sign-blind $T(t_f)-T_{sp}$ (K)"
    smax = [c for c in tab[0] if c.startswith("$S_")]
    body = []
    for name in SIX:
        r = next(x for x in tab if x["Method"] == name and x["Quantity"] == ratio)
        vals = [num(r[c]) for c in smax]
        s = SHORT[name].replace(" ", "")
        define(f"map{s}min", min(vals), "smax_regime_map", "{:.1f}")
        define(f"map{s}max", max(vals), "smax_regime_map", "{:.1f}")
        define(f"map{s}twenty", vals[0], "smax_regime_map", "{:.1f}")
        define(f"map{s}eighty", vals[smax.index("$S_{\\max}=80$")], "smax_regime_map", "{:.1f}")
        define(f"map{s}last", vals[-1], "smax_regime_map", "{:.1f}")
        body.append([SHORT[name]] + [r[c] for c in smax])
    for name in ("Ziegler-Nichols", "Cohen-Coon"):
        r = next(x for x in tab if x["Method"] == name and x["Quantity"] == sign)
        latched = [int(re.findall(r"\d+", c)[0]) for c in smax if abs(num(r[c]) + 16.7) < 0.15]
        define(
            f"latchfrom{SHORT[name]}", f"{min(latched)}", "smax_regime_map (final error -16.7 K)"
        )
    ret = rows("smax_retuned")
    define("retunedfirst", num(ret[0]["ratio"]), "smax_retuned", "{:.1f}")
    define("retunedlast", num(ret[-1]["ratio"]), "smax_retuned", "{:.1f}")
    return [smax, body]


def robustness_extension() -> list[list[str]]:
    """Deadband 6 L/min and second operating point, four policies, one condensed table."""
    pol = (
        ("Sign-blind amp.", "SB"),
        ("Amp. direct.", "Amp."),
        (RATE, "Rate"),
        (BC_SQRT, "BC"),
        (BC_CV, "BC$^{\\mathrm{cv}}$"),
    )
    body = []
    for name in SIX:
        row = [SHORT[name]]
        for col, _ in pol:
            row.append(
                f"{num(cell('antiwindup_deadband', col, **{'Deadband (L/min)': '6', 'Method': name})):.2f}"
            )
        for col, _ in pol:
            if name == OPT:
                row.append("--")
            else:
                row.append(f"{num(cell('antiwindup_second_op', col, Method=name)):.2f}")
        body.append(row)
    for band in ("3", "6"):
        b = {"3": "three", "6": "six"}[band]
        define(
            f"dbAMIGOdir{b}",
            num(cell("antiwindup_deadband", RATE, **{"Deadband (L/min)": band, "Method": "AMIGO"})),
            "antiwindup_deadband",
        )
        for name in ("Ziegler-Nichols", "Cohen-Coon"):
            m = {"Deadband (L/min)": band, "Method": name}
            for col, tag in (("Sign-blind amp.", "sign"), ("Amp. direct.", "amp"), (RATE, "dir")):
                define(
                    f"db{SHORT[name]}{tag}{b}",
                    num(cell("antiwindup_deadband", col, **m)),
                    "antiwindup_deadband",
                )
    ratios = [
        num(cell("antiwindup_deadband", RATE, **{"Deadband (L/min)": "6", "Method": n}))
        / num(cell("antiwindup_deadband", BC_SQRT, **{"Deadband (L/min)": "6", "Method": n}))
        for n in SIX
    ]
    define("dbsixworstpct", 100.0 * (max(ratios) - 1.0), "antiwindup_deadband", "{:.0f}")
    define("dbampratiomin", min(
        num(cell("antiwindup_deadband", "Amp. direct.", **{"Deadband (L/min)": "6", "Method": n}))
        / num(cell("antiwindup_deadband", RATE, **{"Deadband (L/min)": "6", "Method": n}))
        for n in ("Ziegler-Nichols", "Cohen-Coon")), "antiwindup_deadband (amp-only / rate, ZN and CC)", "{:.0f}")
    ratios_cv = [
        num(cell("antiwindup_deadband", RATE, **{"Deadband (L/min)": "6", "Method": n}))
        / num(cell("antiwindup_deadband", BC_CV, **{"Deadband (L/min)": "6", "Method": n}))
        for n in SIX
    ]
    define("dbsixworstpctcv", 100.0 * (max(ratios_cv) - 1.0), "antiwindup_deadband (rate rule vs BC T_t^cv)", "{:.0f}")
    for name in ("Ziegler-Nichols", "Cohen-Coon", "AMIGO", "Skogestad SIMC"):
        s = SHORT[name]
        for col, tag in (
            ("None", "none"),
            ("Sign-blind amp.", "sign"),
            ("Amp. direct.", "amp"),
            (RATE, "dir"),
        ):
            define(
                f"op{s}{tag}",
                num(cell("antiwindup_second_op", col, Method=name)),
                "antiwindup_second_op",
            )
    return [[c for _, c in pol], body]


def rate_trigger_numbers() -> None:
    """SIMC as the counterexample of the slew-rate trigger, and what the rate demand rho tells."""
    simc = "Skogestad SIMC"
    for col, tag in (("None", "none"), (RATE, "dir")):
        define(f"SIMC{tag}", num(cell("antiwindup_ablation", col, Method=simc)), "antiwindup_ablation")
        for scen, s in (("$-5$ K step", "m"), ("$+5$ K step", "p")):
            define(f"SIMCfive{s}{tag}", num(cell("antiwindup_scenarios", col, Scenario=scen, Method=simc)),
                   "antiwindup_scenarios")
        define(f"dbSIMC{tag}six",
               num(cell("antiwindup_deadband", col, **{"Deadband (L/min)": "6", "Method": simc})),
               "antiwindup_deadband")
    grid = rows("rate_demand_grid")
    for r in grid:
        for k in ("ratio", "rho", "step_K", "S_max"):
            r[k] = float(r[k])
    for smax, tag in ((20.0, "twenty"), (45.0, "ff"), (80.0, "eighty"), (320.0, "last")):
        r = next(x for x in grid if x["Method"] == simc and x["step_K"] == -2.0 and x["S_max"] == smax)
        define(f"SIMCratio{tag}", r["ratio"], "rate_demand_grid (IAE_amp/IAE_rate, -2 K)")
    at80 = [r for r in grid if r["S_max"] == 80.0]
    trl = {r["Method"]: float(r["T_rl_min"]) for r in at80 if r["step_K"] == -2.0}
    define("TrlSIMC", trl[simc], "rate_demand_grid (time slew-limited, -2 K, S_max = 80)")
    define("Trlothersmin", min(v for k, v in trl.items() if k != simc), "rate_demand_grid")
    define("Trlothersmax", max(v for k, v in trl.items() if k != simc), "rate_demand_grid")
    define("rhoSIMCmaxeighty", max(r["rho"] for r in at80 if r["Method"] == simc), "rate_demand_grid")
    define("rhoothersmineighty", min(r["rho"] for r in at80 if r["Method"] != simc), "rate_demand_grid")
    hi, lo = [r for r in grid if r["rho"] >= 1.0], [r for r in grid if r["rho"] < 1.0]
    define("ncases", f"{len(grid)}", "rate_demand_grid (6 loops x 3 steps x 9 S_max)")
    define("nrhohi", f"{len(hi)}", "rate_demand_grid (cases with rho >= 1)")
    define("nrhohihelp", f"{sum(r['ratio'] > 1.0 for r in hi)}", "rate_demand_grid (rho >= 1, ratio > 1)")
    define("rhohiratiomin", min(r["ratio"] for r in hi), "rate_demand_grid (worst ratio with rho >= 1)")
    define("rholoratiomin", min(r["ratio"] for r in lo), "rate_demand_grid (ratio range with rho < 1)")
    define("rholoratiomax", max(r["ratio"] for r in lo), "rate_demand_grid (ratio range with rho < 1)")
    hurt_lo = [r for r in lo if r["ratio"] < 1.0]
    if {r["Method"] for r in hurt_lo} != {simc}:
        raise ValueError("text states that every rho < 1 case made worse by the trigger is SIMC")
    define("nrholohurt", f"{len(hurt_lo)}", "rate_demand_grid (rho < 1, ratio < 1: all SIMC)")
    helped = min((r for r in lo if r["ratio"] > 1.0), key=lambda r: r["rho"])
    define("rhohelplow", helped["rho"], "rate_demand_grid (lowest rho of a helped case)")
    define("rhohelplowratio", helped["ratio"], "rate_demand_grid")
    define("rhohelplowloop", SHORT[helped["Method"]], "rate_demand_grid")
    define("rhohelplowsmax", f"{helped['S_max']:.0f}", "rate_demand_grid")


def rate_demand_check_numbers() -> None:
    """The rho >= 1 rule on the second operating point and the deadbands (rate_demand_check)."""
    tab = rows("rate_demand_check")
    ratio = "\\(\\mathrm{IAE}_{\\mathrm{amp}}/\\mathrm{IAE}_{\\mathrm{rate}}\\)"
    hi = [r for r in tab if num(r["\\(\\rho\\)"]) >= 1.0]
    lo = [r for r in tab if num(r["\\(\\rho\\)"]) < 1.0]
    define("chkcases", f"{len(tab)}", "rate_demand_check")
    define("chkrhohi", f"{len(hi)}", "rate_demand_check (rho >= 1)")
    define("chkrhohihelp", f"{sum(num(r[ratio]) > 1.0 for r in hi)}", "rate_demand_check (rho >= 1, ratio > 1)")
    define("chkrholo", f"{len(lo)}", "rate_demand_check (rho < 1)")
    for name in ("AMIGO", "Skogestad SIMC"):
        vals = [num(r[ratio]) for r in lo if r["Method"] == name]
        define(f"chklo{SHORT[name]}min", min(vals), "rate_demand_check (rho < 1)")
        define(f"chklo{SHORT[name]}max", max(vals), "rate_demand_check (rho < 1)")
    loops = [SHORT[m] for m in SIX if any(r["Method"] == m for r in hi)]
    define("chkhiloops", f"{len(loops)}", "rate_demand_check (loops with a rho >= 1 case)")
    define("chkhilooplist", ", ".join(loops[:-1]) + " and " + loops[-1], "rate_demand_check")
    near = sorted((r for r in hi if num(r["\\(\\rho\\)"]) < 2.0), key=lambda r: (SIX.index(r["Method"]), num(r["\\(\\rho\\)"])))
    by = {}
    for r in near:
        by.setdefault(SHORT[r["Method"]], []).append(r["\\(\\rho\\)"])
    define("chknear", f"{len(near)}", "rate_demand_check (rho >= 1 cases with rho < 2)")
    define("chknearlist", "; ".join(f"{k} $\\rho = " + "$ and $".join(v) + "$" for k, v in by.items()),
           "rate_demand_check (cases near the threshold, rho < 2)")
    if {r["Method"] for r in lo} != {"AMIGO", "Skogestad SIMC"}:
        raise ValueError("text names AMIGO and SIMC as the rho < 1 cases of the check")


def noise_policy_numbers() -> None:
    """Policies under sensor noise (noise_policies): does back-calculation keep up with the rule?"""
    bc, dr = "IAE BC ($T_t^{\\mathrm{cv}}$)", "IAE Directional"
    for sigma, tag in (("0.01", "lo"), ("0.05", "hi")):
        sel = [r for r in rows("noise_policies") if r["\\(\\sigma\\) (K)"] == sigma]
        ratio = {r["Method"]: num(r[bc]) / num(r[dr]) for r in sel}
        define(f"nzbc{tag}min", min(ratio.values()), "noise_policies (IAE BC / IAE directional)")
        define(f"nzbc{tag}max", max(ratio.values()), "noise_policies (IAE BC / IAE directional)")
        define(f"nzbc{tag}maxpct", 100.0 * (max(ratio.values()) - 1.0), "noise_policies", "{:.0f}")
        if tag == "hi":
            worse = [SHORT[m] for m in SIX if ratio[m] > 1.0]
            better = [SHORT[m] for m in SIX if ratio[m] < 1.0]
            join = lambda xs: ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else xs[0]  # noqa: E731
            define("nzbcworse", join(worse), "noise_policies (BC worse than the rule, sigma 0.05)")
            define("nzbcbetter", join(better), "noise_policies (BC better than the rule, sigma 0.05)")
            simc = next(r for r in sel if r["Method"] == "Skogestad SIMC")
            define("nzSIMCdir", num(simc[dr]), "noise_policies (sigma 0.05)")
            define("nzSIMCnone", num(simc["IAE None"]), "noise_policies (sigma 0.05)")
            emp = [num(r["IAE None"]) / num(r[dr]) for r in sel if r["Method"] in ("Ziegler-Nichols", "Cohen-Coon")]
            define("nzempnonemin", min(emp), "noise_policies (IAE none / IAE directional, ZN and CC)", "{:.0f}")


def noise_round_numbers() -> None:
    """Block B of v9: T_t re-chosen under noise, mechanism, rho under noise, extended policies."""
    join = lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]  # noqa: E731
    tab = rows("noise_ttcv")
    ttcol = "\\(T_t^{\\mathrm{cv}}\\), \\(T_t^{\\mathrm{cv,noise}}\\) (min)"
    bc, bcn, dr = "IAE BC ($T_t^{\\mathrm{cv}}$)", "IAE BC ($T_t^{\\mathrm{cv,noise}}$)", "IAE Directional"
    changed = [SHORT[r["Method"]] for r in tab if r[ttcol] and len(set(r[ttcol].split(", "))) == 2]
    define("nzttchanged", join(changed), "noise_ttcv (loops whose T_t changes under noise)")
    two = [r for r in tab if r["Step"] == "$-2$ K" and SHORT[r["Method"]] in changed]
    define("nzttbeforemax", max(num(r[bc]) / num(r[dr]) for r in two), "noise_ttcv (-2 K, BC/dir, noise-free T_t)")
    define("nzttaftermax", max(num(r[bcn]) / num(r[dr]) for r in two), "noise_ttcv (-2 K, BC/dir, noise T_t)")
    five = [r for r in tab if r["Step"] != "$-2$ K" and SHORT[r["Method"]] in changed]
    define("nzttfiveaftermax", max(num(r[bcn]) / num(r[dr]) for r in five), "noise_ttcv (+-5 K, BC/dir, noise T_t)")
    mech = rows("noise_mechanism")
    emp = [r for r in mech if r["Method"] in ("Ziegler-Nichols", "Cohen-Coon")]
    rb, rd = "RMS \\(I - I_0\\) BC ($T_t^{\\mathrm{cv}}$)", "RMS \\(I - I_0\\) Directional"
    define("mechcutmin", min(num(r["cut share Directional"]) for r in emp), "noise_mechanism (ZN, CC)")
    define("mechrmsratiomin", min(num(r[rb]) / num(r[rd]) for r in emp), "noise_mechanism (ZN, CC)", "{:.0f}")
    define("mechrmsratiomax", max(num(r[rb]) / num(r[rd]) for r in emp), "noise_mechanism (ZN, CC)", "{:.0f}")
    define("mechtrackmin", min(num(r["mean tracking step (L/min)"]) for r in emp), "noise_mechanism (ZN, CC)", "{:.1f}")
    define("mechtrackmax", max(num(r["mean tracking step (L/min)"]) for r in emp), "noise_mechanism (ZN, CC)", "{:.1f}")
    if any(r["cut share Directional"] != r["cut share BC ($T_t^{\\mathrm{cv}}$)"] for r in emp):
        raise ValueError("text states that both policies are cut in the same share of samples")
    grid = rows("rho_noise_grid")
    for r in grid:
        for k in ("sigma", "tau_m", "rho", "R"):
            r[k] = float(r[k])
    for sg, tau, tag in ((0.0, 0.0, "free"), (0.05, 0.0, "raw"), (0.05, 0.05, "filt")):
        sel = [r for r in grid if r["sigma"] == sg and r["tau_m"] == tau]
        define(f"rhonz{tag}wrong", f"{sum(r['rho'] >= 1.0 and r['R'] < 1.0 for r in sel)}",
               "rho_noise_grid (rho >= 1 but the trigger makes the loop worse)")
        define(f"rhonz{tag}SIMCmax", max(r["rho"] for r in sel if r["Method"] == "Skogestad SIMC"), "rho_noise_grid")
    define("rhonzcases", f"{sum(r['sigma'] == 0.0 for r in grid)}", "rho_noise_grid")
    ext = rows("noise_policies_ext_full")
    iae = {(r["Method"], r["policy"], float(r["step_K"]), float(r["sigma"]), float(r["tau_m"])): float(r["IAE_mean"])
           for r in ext}
    keys = {k[:1] + k[2:] for k in iae}
    ratio = {k: iae[(k[0], "BC", *k[1:])] / iae[(k[0], "Dir", *k[1:])] for k in keys}
    define("extrawmax", max(v for k, v in ratio.items() if k[2] == 0.05 and k[3] == 0.0), "noise_policies_ext_full (BC/dir, 0.05 K, raw)")
    define("extfiltmax", max(v for k, v in ratio.items() if k[3] > 0.0), "noise_policies_ext_full (BC/dir, filtered)")
    none = [iae[(k[0], "None", *k[1:])] / iae[(k[0], "Dir", *k[1:])] for k in keys if k[0] in ("Ziegler-Nichols", "Cohen-Coon")]
    define("extempnonemin", min(none), "noise_policies_ext_full (none/dir, ZN and CC)", "{:.0f}")


def order_variant_numbers() -> None:
    """D2: order of limits and filters (order_variants, order_variants_flips, _full)."""
    tab = rows("order_variants")
    dcol = "max \\(|\\Delta\\)IAE\\(|\\) (\\%)"
    tags = {"(i)": "One", "(ii)": "Two", "(iii)": "Three", "(iv)": "Four"}
    for r in tab:
        t = tags[r["Variant"].split()[0]] + ("Noisy" if r["\\(\\sigma\\) (K)"] != "0" else "")
        define(f"order{t}dIAE", num(r[dcol]), "order_variants", "{:.1f}")
        define(f"order{t}rank", "changes" if "changes" in (r["loop ranking"], r["policy ranking"]) else "same",
               "order_variants")
    seen = {n: v for n, v, _ in MACROS if n.startswith("order") and n.endswith("rank")}
    expect = {"orderOnerank": "same", "orderTworank": "changes", "orderThreerank": "same",
              "orderThreeNoisyrank": "changes", "orderFourrank": "changes", "orderFourNoisyrank": "changes"}
    if seen != expect:
        raise ValueError(f"text states which order variants change a ranking: {seen}")
    fl = rows("order_variants_flips")
    working = ("Rate", "BC", "BC$^{\\mathrm{cv}}$")
    pol = [r for r in fl if r["kind"] == "policies"]
    work = [r for r in pol if all(p in working for p in r["flip"].split(": ")[1].split("<"))]
    define("dtwopolflips", f"{len(pol)}", "order_variants_flips (policy-order swaps, all variants)")
    define("dtwoworkflips", f"{len(work)}", "order_variants_flips (swaps among Rate, BC, BC^cv)")
    full = rows("order_variants_full")
    iae = {(r["Method"], r["policy"], r["variant"], r["sigma"], r["step_K"]): float(r["IAE"]) for r in full}
    combos = {(k[2], k[3]) for k in iae}
    sb, amp = [], []
    for v, sg in combos:
        for n in ("Ziegler-Nichols", "Cohen-Coon"):
            for st in {k[4] for k in iae}:
                rate = iae[(n, "Rate", v, sg, st)]
                sb.append(iae[(n, "SB", v, sg, st)] / rate)
                amp.append(iae[(n, "Amp.", v, sg, st)] / rate)
    define("dtwosbmin", min(sb), "order_variants_full (SB/Rate, ZN and CC, every variant)", "{:.0f}")
    define("dtwoampmin", min(amp), "order_variants_full (Amp/Rate, ZN and CC, every variant)", "{:.1f}")


def hx_numbers() -> list[list[str]]:
    """C1: second plant (hx_model, hx_ablation, hx_rate_demand_grid); returns the condensed table."""
    mod = rows("hx_model")[0]
    for k, tag, fmt in (("K", "K", "{:.3f}"), ("tau_min", "tau", "{:.3f}"), ("theta_min", "theta", "{:.3f}"),
                        ("r", "r", "{:.2f}"), ("T2_ss_K", "Tss", "{:.1f}"), ("T2_at_umax_K", "Tinf", "{:.1f}"),
                        ("eig_1", "eigfast", "{:.2f}"), ("eig_3", "eigslow", "{:.2f}")):
        define(f"hx{tag}", float(mod[k]), "hx_model", fmt)
    ab = rows("hx_ablation")
    iae = {(r["Step"], r["Method"], c): num(r[c]) for r in ab for c in r if c not in ("Step", "Method")}
    steps = ("$-2$ K", "$-5$ K", "$+5$ K")
    emp = ("Ziegler-Nichols", "Cohen-Coon")
    amp, sb, none = "Amp. direct.", "Sign-blind amp.", "None"
    define("hxampratemin", min(iae[(s, n, amp)] / iae[(s, n, RATE)] for s in steps[1:] for n in emp),
           "hx_ablation (Amp/Rate, ZN and CC, +-5 K)", "{:.0f}")
    sbr = [iae[(s, n, sb)] / iae[(s, n, none)] for s in steps[1:] for n in emp]
    define("hxsbnonemin", min(sbr), "hx_ablation (SB/None, ZN and CC, +-5 K)")
    define("hxsbnonemax", max(sbr), "hx_ablation (SB/None, ZN and CC, +-5 K)")
    if any(num(r["SB at \\(u_{\\max}\\) (min)"]) > 0.0 for r in ab):
        raise ValueError("text states that sign-blind clamping never rests at the upper stop on the HX")
    tl = [iae[(s, "Tyreus-Luyben", RATE)] / iae[(s, "Tyreus-Luyben", none)] for s in steps]
    define("hxTLratemin", min(tl), "hx_ablation (TL rate/none)")
    define("hxTLratemax", max(tl), "hx_ablation (TL rate/none)")
    simc = [iae[(s, "Skogestad SIMC", RATE)] / iae[(s, "Skogestad SIMC", none)] for s in steps]
    define("hxSIMCworse", f"{sum(v > 1.0 for v in simc)}", "hx_ablation (steps where the rule worsens SIMC)")
    bc = [iae[(s, n, BC_CV)] / iae[(s, n, RATE)] for s in steps for n in SIX]
    define("hxbcmin", min(bc), "hx_ablation (BC T_t^cv / rate, all loops and steps)")
    define("hxbcmax", max(bc), "hx_ablation (BC T_t^cv / rate, all loops and steps)")
    grid = rows("hx_rate_demand_grid")
    for r in grid:
        r["R"], r["rho"] = float(r["R"]), float(r["rho"])
    hi = [r for r in grid if r["rho"] >= 1.0]
    define("hxnrhohi", f"{len(hi)}", "hx_rate_demand_grid (rho >= 1)")
    define("hxnrhohihelp", f"{sum(r['R'] > 1.0 for r in hi)}", "hx_rate_demand_grid (rho >= 1, R > 1)")
    bad = [r for r in hi if r["R"] <= 1.0]
    badl = [SHORT[m] for m in SIX if any(r["Method"] == m for r in bad)]
    define("hxbadloops", " and ".join(badl), "hx_rate_demand_grid (rho >= 1, R <= 1)")
    define("hxbadrhomax", max(r["rho"] for r in bad), "hx_rate_demand_grid", "{:.0f}")
    define("hxbadRmin", min(r["R"] for r in bad), "hx_rate_demand_grid")
    define("hxncases", f"{len(grid)}", "hx_rate_demand_grid")
    body = []
    for n in SIX:
        body.append([SHORT[n]] + [f"{iae[('$-5$ K', n, c)]:.2f}" for c in (none, sb, amp, RATE, BC_CV)]
                    + [f"{iae[('$-2$ K', n, c)]:.2f}" for c in (none, RATE)])
    return body


def stiction_numbers() -> None:
    """C3: stiction (stiction_full)."""
    d = rows("stiction_full")
    for r in d:
        for k in ("IAE", "step_K"):
            r[k] = float(r[k])
    iae = {(r["severity"], r["Method"], r["policy"], r["step_K"]): r["IAE"] for r in d}
    work = ("Amp.", "Rate", "BC", "BC$^{\\mathrm{cv}}$")
    for sev in ("moderate", "severe"):
        sel = [r for r in d if r["severity"] == sev and r["policy"] in work]
        define(f"stick{sev}hunt", 100.0 * sum(r["hunting"] == "True" for r in sel) / len(sel),
               "stiction_full (share of hunting runs, policies other than SB)", "{:.0f}")
    stuck = [r for r in d if r["severity"] != "none"]
    emp = ("Ziegler-Nichols", "Cohen-Coon")
    define("sticksbmin", min(iae[(r["severity"], r["Method"], "SB", r["step_K"])] / iae[(r["severity"], r["Method"], "Rate", r["step_K"])]
                             for r in stuck if r["Method"] in emp), "stiction_full (SB/Rate, ZN and CC)", "{:.0f}")
    define("stickampmin", min(iae[(r["severity"], r["Method"], "Amp.", r["step_K"])] / iae[(r["severity"], r["Method"], "Rate", r["step_K"])]
                              for r in stuck if r["Method"] in emp), "stiction_full (Amp/Rate, ZN and CC)", "{:.1f}")
    bc = [iae[(r["severity"], r["Method"], "BC$^{\\mathrm{cv}}$", r["step_K"])] / iae[(r["severity"], r["Method"], "Rate", r["step_K"])]
          for r in stuck]
    define("stickbcmin", min(bc), "stiction_full (BC^cv/Rate)")
    define("stickbcmax", max(bc), "stiction_full (BC^cv/Rate)")
    simc = [iae[(s, "Skogestad SIMC", "Rate", st)] / iae[(s, "Skogestad SIMC", "Amp.", st)]
            for s in ("moderate", "severe") for st in (-2.0, -5.0, 5.0)]
    define("stickSIMCmin", min(simc), "stiction_full (SIMC Rate/Amp = Rate/None)")
    define("stickSIMCmax", max(simc), "stiction_full (SIMC Rate/Amp = Rate/None)")


def measured_position_numbers() -> None:
    """C4: anti-windup with a measured valve position (measured_position_full)."""
    d = rows("measured_position_full")
    for r in d:
        for k in ("IAE", "spurious_freeze", "step_K"):
            r[k] = float(r[k])
    get = {(r["Method"], r["case"], r["step_K"]): r for r in d}
    base, meas = "Rate, $u_{\\text{act}}$", "Rate, $u_{\\text{meas}}$"
    band = "Rate, $u_{\\text{meas}}$, $\\varepsilon_u$"
    bca, bcm = "BC$^{\\mathrm{cv}}$, $u_{\\text{act}}$", "BC$^{\\mathrm{cv}}$, $u_{\\text{meas}}$"
    keys = {(r["Method"], r["step_K"]) for r in d}
    sp = [get[(n, meas, s)]["spurious_freeze"] for n, s in keys]
    define("posspurmin", 100 * min(sp), "measured_position_full (spurious freezes, no band)", "{:.0f}")
    define("posspurmax", 100 * max(sp), "measured_position_full (spurious freezes, no band)", "{:.0f}")
    define("posspurbandmax", 100 * max(get[(n, band, s)]["spurious_freeze"] for n, s in keys),
           "measured_position_full (spurious freezes, band)", "{:.0f}")
    worse = max(keys, key=lambda k: get[(k[0], meas, k[1])]["IAE"] / get[(k[0], base, k[1])]["IAE"])
    define("posworstpct", 100 * (get[(worse[0], meas, worse[1])]["IAE"] / get[(worse[0], base, worse[1])]["IAE"] - 1),
           "measured_position_full (largest IAE rise, no band)", "{:.0f}")
    define("posworstloop", SHORT[worse[0]], "measured_position_full")
    define("posbandpct", 100 * max(abs(get[(n, band, s)]["IAE"] / get[(n, base, s)]["IAE"] - 1) for n, s in keys),
           "measured_position_full (largest |IAE change| with the band)", "{:.0f}")
    define("posbcpct", 100 * max(get[(n, bcm, s)]["IAE"] / get[(n, bca, s)]["IAE"] - 1 for n, s in keys),
           "measured_position_full (largest IAE rise of BC with u_meas)", "{:.0f}")


def c2_numbers() -> None:
    """C2: operating point by the declared criterion (c2_candidates, c2_ablation, c2_rate_demand)."""
    from src.sim_core.cstr_plant import CSTRPlant

    cand = rows("c2_candidates")
    chosen = min((r for r in cand if r["eligible"] == "True"), key=lambda r: float(r["slack"]))
    q = float(chosen["q_j_ss"])
    define("ctwoq", q, "c2_candidates (selected point)", "{:.0f}")
    define("ctwoslack", float(chosen["slack"]), "c2_candidates")
    plant = CSTRPlant()
    t_ss = plant.find_steady_state(q_j=q).T
    ureq = plant.required_coolant_flow(t_ss - 5.0)
    if ureq <= 300.0:
        raise ValueError("text states that the -5 K setpoint is beyond the valve at the C2 point")
    define("ctwoureq", ureq, "CSTRPlant.required_coolant_flow(T_ss - 5) at the C2 point", "{:.0f}")
    ab = rows("c2_ablation")
    iae = {(r["Method"], r["Step"], c): num(r[c]) for r in ab for c in r if c not in ("Method", "Step")}
    loops = ("Ziegler-Nichols", "Cohen-Coon", "AMIGO")
    p5 = "$+5$ K"
    define("ctwosbmin", min(iae[(n, p5, "Sign-blind amp.")] / iae[(n, p5, "None")] for n in loops), "c2_ablation")
    define("ctwoampmin", min(iae[(n, p5, "Amp. direct.")] / iae[(n, p5, RATE)] for n in loops), "c2_ablation", "{:.1f}")
    define("ctwoampmax", max(iae[(n, p5, "Amp. direct.")] / iae[(n, p5, RATE)] for n in loops), "c2_ablation", "{:.1f}")
    rd = rows("c2_rate_demand")
    hi = [r for r in rd if float(r["rho"]) >= 1.0]
    define("ctworhohi", f"{len(hi)}", "c2_rate_demand (rho >= 1)")
    define("ctworhohelp", f"{sum(float(r['R']) > 1.005 for r in hi)}", "c2_rate_demand (rho >= 1, R > 1.005)")
    define("ctworhotie", f"{sum(abs(float(r['R']) - 1.0) <= 0.005 for r in hi)}", "c2_rate_demand (rho >= 1, |R - 1| <= 0.005)")
    tl = next(r for r in rd if r["Method"] == "Tyreus-Luyben" and float(r["step_K"]) == -2.0)
    define("ctwoTLrho", float(tl["rho"]), "c2_rate_demand")
    define("ctwoTLR", float(tl["R"]), "c2_rate_demand")


def predictive_and_exact_numbers() -> None:
    """Freeze test at k (predictor-corrector) and exact back-calculation factor (Tables S)."""
    pc = rows("predictive_clamping")
    dpc = "\\(\\Delta\\)IAE (\\%)"
    worst = {}
    for r in pc:
        worst[r["Method"]] = max(worst.get(r["Method"], 0.0), abs(num(r[dpc])))
    for name in ("Ziegler-Nichols", "Cohen-Coon"):
        define(f"pc{SHORT[name]}maxpct", worst[name], "predictive_clamping (largest |dIAE| over 3 steps)", "{:.1f}")
        for col, tag in (("IAE, \\(k-1\\)", "old"), ("IAE, \\(k\\)", "new")):
            define(f"pc{SHORT[name]}five{tag}", num(cell("predictive_clamping", col, Method=name, Step="$+5$ K")),
                   "predictive_clamping", "{:.2f}")
    define("pcnommaxpct", max(abs(num(r[dpc])) for r in pc if r["Step"] == "$-2$ K"),
           "predictive_clamping (largest |dIAE| on the nominal -2 K step)", "{:.1f}")
    define("pcrestmaxpct", max(v for n, v in worst.items() if n not in ("Ziegler-Nichols", "Cohen-Coon")),
           "predictive_clamping (largest |dIAE| of TL, AMIGO, SIMC, Optimal ITAE)", "{:.1f}")
    simc = [r for r in pc if r["Method"] == "Skogestad SIMC"]
    none = [num(cell("antiwindup_ablation", "None", Method="Skogestad SIMC"))] + [
        num(cell("antiwindup_scenarios", "None", Scenario=sc, Method="Skogestad SIMC"))
        for sc in ("$-5$ K step", "$+5$ K step")
    ]
    if not all(num(r["IAE, \\(k\\)"]) > n for r, n in zip(simc, none)):
        raise ValueError("text states that SIMC stays worse than no anti-windup with the test at k")
    tv = rows("antiwindup_tt_tvmp")
    ratios = {}
    for r, p in zip(tv, pc, strict=True):
        if (r["Method"], r["Step"]) != (p["Method"], p["Step"]):
            raise ValueError("antiwindup_tt_tvmp and predictive_clamping rows are not aligned")
        if r["Step"] != "$-2$ K":
            ratios[r["Method"]] = max(ratios.get(r["Method"], 0.0), num(r["IAE BC"]) / num(p["IAE, \\(k\\)"]))
    define("pcttcvmin", min(ratios.values()), "antiwindup_tt_tvmp / predictive_clamping (+-5 K worst ratio)")
    define("pcttcvmax", max(ratios.values()), "antiwindup_tt_tvmp / predictive_clamping (+-5 K worst ratio)")
    for name in ("Ziegler-Nichols", "Cohen-Coon"):
        m = {"Method": name, "Step": "$-2$ K"}
        define(f"ex{SHORT[name]}ratio", num(cell("exact_backcalc", "\\(\\Delta t/T_t\\)", **m)), "exact_backcalc")
        define(f"ex{SHORT[name]}euler", num(cell("exact_backcalc", "IAE Euler", **m)), "exact_backcalc")
        define(f"ex{SHORT[name]}exact", num(cell("exact_backcalc", "IAE exact", **m)), "exact_backcalc")
        define(f"ex{SHORT[name]}TVeuler", num(cell("exact_backcalc", "TV Euler (L/min)", **m)), "exact_backcalc", "{:.0f}")


def shapley_numbers() -> None:
    """Shapley effects on the feasible region, mean and 95 % half-width over seeds (Table S)."""
    tab = rows("sobol_shapley")
    fac = {"ea": "$E_a/R$", "ua": "$UA$", "caf": "$C_{Af}$", "th": "$\\theta_{\\mathrm{sensor}}$"}
    r2 = "\\(R^2\\) (all four)"
    iae = [r for r in tab if r["Metric"] == "IAE"]
    for tag, col in (*fac.items(), ("rtwo", r2)):
        vals = [num(r[col]) for r in iae]
        define(f"shapIAE{tag}min", min(vals), "sobol_shapley (mean over seeds, IAE)")
        define(f"shapIAE{tag}max", max(vals), "sobol_shapley (mean over seeds, IAE)")
    tv = {r["Method"]: r for r in tab if r["Metric"] == "TV"}
    define("shapTVZNth", num(tv["Ziegler-Nichols"][fac["th"]]), "sobol_shapley (TV)")
    define("shapTVCCth", num(tv["Cohen-Coon"][fac["th"]]), "sobol_shapley (TV)")
    define("shapTVCCea", num(tv["Cohen-Coon"][fac["ea"]]), "sobol_shapley (TV)")
    group = ("Tyreus-Luyben", OPT, "2-DOF Optimal ITAE")
    ea = [num(tv[m][fac["ea"]]) for m in group]
    define("shapTVgroupeamin", min(ea), "sobol_shapley (TV, TL and optimal tunings)")
    define("shapTVgroupeamax", max(ea), "sobol_shapley (TV, TL and optimal tunings)")
    define("shapTVSIMCcaf", num(tv["Skogestad SIMC"][fac["caf"]]), "sobol_shapley (TV)")
    rt = [num(r[r2]) for r in tv.values()]
    define("shapTVrtwomin", min(rt), "sobol_shapley (TV)")
    define("shapTVrtwomax", max(rt), "sobol_shapley (TV)")
    hw = [float(r["max_half_width"]) for r in rows("sobol_shapley_halfwidth")]
    define("shaphwmax", max(hw), "sobol_shapley_halfwidth (largest 95 % half-width over seeds)", "{:.3f}")


def testbed_table() -> list[list[str]]:
    """Gains, nominal metrics and robustness of the six feedback loops."""
    body = []
    for name in SIX:
        b = {
            k: cell("benchmark_table", k, Method=name)
            for k in (
                "\\(K_p\\)",
                "\\(T_i\\text{ (min)}\\)",
                "\\(T_d\\text{ (min)}\\)",
                "IAE",
                "TV (L/min)",
                "\\(M_p\\text{ (\\%)}\\)",
                "\\(M_s\\)",
            )
        }
        e = {
            k: cell("exact_robustness_table", k, Method=name)
            for k in ("\\(\\|S\\|_\\infty\\) (lin.)", "\\(\\|CS\\|_\\infty\\) (L/min/K)")
        }
        body.append([SHORT[name], *b.values(), *e.values()])
        s = SHORT[name].replace(" ", "")
        define(f"Slin{s}", num(e["\\(\\|S\\|_\\infty\\) (lin.)"]), "exact_robustness_table")
        define(
            f"CS{s}", num(e["\\(\\|CS\\|_\\infty\\) (L/min/K)"]), "exact_robustness_table", "{:.0f}"
        )
        define(f"MsF{s}", num(b["\\(M_s\\)"]), "benchmark_table")
    return body


def measurement_numbers() -> None:
    """Measurement filter and derivative-filter coefficient (supplementary noise campaign)."""
    tab = rows("noise_chattering_table")
    tv = {
        (r["Method"], r["$\\tau_m$ (min)"]): num(r["TV (L/min)"])
        for r in tab
        if r["Noise $\\sigma$ (K)"] == "0.01"
    }
    factors = [tv[(m, "0.00")] / tv[(m, "0.05")] for m, t in tv if t == "0.00"]
    define("filtfactmin", min(factors), "noise_chattering_table", "{:.1f}")
    define("filtfactmax", max(factors), "noise_chattering_table", "{:.1f}")
    nd = rows("n_design_sweep")
    cuts = []
    for name in ("Ziegler-Nichols", "Cohen-Coon"):
        k = {
            r["\\(N\\)"]: num(r["\\(K_{\\mathrm{hf}}\\) (L/min/K)"])
            for r in nd
            if r["Method"] == name
        }
        cuts.append(100.0 * (1.0 - k["3"] / k["10"]))
    define("Ncut", min(cuts), "n_design_sweep", "{:.0f}")


def load_table() -> list[list[str]]:
    """Deterministic load response of the six feedback loops."""
    tab = rows("disturbance_rejection_table")
    cols = ["IAE", "TV (L/min)", "Peak Dev (K)", "Max Valve (L/min)"]
    body = []
    for name in SIX:
        r = next(x for x in tab if x["Method"] == name)
        body.append([SHORT[name]] + [r[c] for c in cols])
        define(f"load{SHORT[name].replace(' ', '')}", num(r["IAE"]), "disturbance_rejection_table")
    peaks = [num(r[2]) for r in [[b[0], b[1], b[3]] for b in body]]
    define("loadpeakmin", min(peaks), "disturbance_rejection_table")
    define("loadpeakmax", max(peaks), "disturbance_rejection_table")
    valves = [num(b[4]) for b in body]
    define("loadvalvemin", min(valves), "disturbance_rejection_table", "{:.1f}")
    define("loadvalvemax", max(valves), "disturbance_rejection_table", "{:.1f}")
    return [cols, body]


def main() -> None:
    """Writes numbers.tex, the condensed tables and the provenance CSV."""
    ablation_numbers()
    signblind_numbers()
    proposition_numbers()
    latch_check_numbers()
    back_calculation_numbers()
    back_calculation_detail()
    regime_map()
    pol, ext_body = robustness_extension()
    tb_body = testbed_table()
    measurement_numbers()
    rate_trigger_numbers()
    rate_demand_check_numbers()
    noise_policy_numbers()
    noise_round_numbers()
    order_variant_numbers()
    hx_body = hx_numbers()
    stiction_numbers()
    measured_position_numbers()
    c2_numbers()
    predictive_and_exact_numbers()
    shapley_numbers()
    load_cols, load_body = load_table()

    tables = PAPER / "tables"
    (tables / "v7_testbed.tex").write_text(
        booktabs(
            [
                "Tuning",
                "\\(K_p\\) ((L/min)/K)",
                "\\(T_i\\) (min)",
                "\\(T_d\\) (min)",
                "IAE",
                "TV (L/min)",
                "\\(M_p\\) (\\%)",
                "\\(M_s^{\\mathrm{FOPTD}}\\)",
                "\\(\\|S\\|_\\infty^{\\mathrm{lin}}\\)",
                "\\(\\|CS\\|_\\infty^{\\mathrm{lin}}\\) ((L/min)/K)",
            ],
            tb_body,
            "Test-bed loops: gains, nominal $-2$~K step with the directional rule (IAE in K$\\cdot$min), "
            "sensitivity peak on the identified FOPTD and on the exact linearization with the half-sample "
            "hold, and the peak of the noise-to-valve gain $CS = C/(1+L)$, which equals "
            "$|K_p|(1+N)$ to within $0.3$~(L/min)/K. Units: $K_p$ and $\\|CS\\|_\\infty$ in (L/min)/K.",
            "tab:testbed",
        ),
        encoding="utf-8",
    )
    (tables / "v9_hx.tex").write_text(
        booktabs(
            ["Tuning", "None", "SB", "Amp.", "Rate", "BC$^{\\mathrm{cv}}$", "None", "Rate"],
            hx_body,
            "Second plant, the heat exchanger of Supplementary Section~\\suppref{supp:hx}: IAE "
            "(K$\\cdot$min) of the integrator policies on the $-5$~K step (first five columns) and of no "
            "anti-windup and the rate-aware rule on the $-2$~K step (last two); same valve "
            "($[0, 300]$~L/min, $S_{\\max} = 80$~L/min$^2$), loops tuned by the same rules, Optimal ITAE "
            "re-optimized, BC$^{\\mathrm{cv}}$ with $T_t^{\\mathrm{cv}}$ chosen on this plant.",
            "tab:hx",
            group=" & \\multicolumn{5}{c}{$-5$~K step} & \\multicolumn{2}{c}{$-2$~K step}",
        ),
        encoding="utf-8",
    )
    (tables / "v7_robustness_ext.tex").write_text(
        booktabs(
            ["Tuning", *pol, *pol],
            ext_body,
            "IAE (K$\\cdot$min) of five integrator policies with a valve deadband of $6$~L/min and at a "
            "second operating point $q_{j,ss} = 150$~L/min with re-identified FOPTD and re-tuned "
            "analytical rules (the optimal tuning was not re-optimized there); valve $[0, 300]$~L/min, "
            "$S_{\\max} = 80$~L/min$^2$. SB: sign-blind amplitude clamping; Amp.: amplitude-only "
            "directional; Rate: amplitude-plus-rate directional (Eq.~\\eqref{eq:clamping_antiwindup}); "
            "BC: back-calculation with $T_t = \\sqrt{T_iT_d}$; BC$^{\\mathrm{cv}}$: with the "
            "$T_t^{\\mathrm{cv}}$ of Table~\\ref{tab:antiwindup_tt_summary}, re-chosen by the same criterion "
            "at the second point.",
            "tab:robustness_ext",
            group=f" & \\multicolumn{{{len(pol)}}}{{c}}{{Deadband $6$~L/min}} & "
            f"\\multicolumn{{{len(pol)}}}{{c}}{{$q_{{j,ss}} = 150$~L/min}}",
        ),
        encoding="utf-8",
    )
    (tables / "v7_load.tex").write_text(
        booktabs(
            ["Tuning", "IAE", "TV", "Peak", "Max \\(q_j\\)"],
            load_body,
            "Deterministic rejection of a $+2$~K feed-temperature step at $t = 2$~min and a $+10\\%$ "
            "feed-concentration step at $t = 8$~min ($15$~min, no noise, directional rule). IAE in "
            "K$\\cdot$min, TV and largest valve opening $q_j$ in L/min, peak deviation in K.",
            "tab:load",
            env="table",
        ),
        encoding="utf-8",
    )

    out = PAPER / "generated"
    out.mkdir(exist_ok=True)
    names = [n for n, _, _ in MACROS]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise ValueError(f"duplicate macros: {sorted(dup)}")
    bad = [n for n in names if not re.fullmatch(r"[A-Za-z]+", n)]
    if bad:
        raise ValueError(f"macro names must be letters only: {bad}")
    body = "\n".join(f"\\newcommand{{\\v{n}}}{{{v}}}  % {src}" for n, v, src in MACROS)
    (out / "numbers.tex").write_text(
        "% Generated by scripts/jpc_v6_numbers.py -- do not edit.\n" + body + "\n", encoding="utf-8"
    )
    with open(RES / "v9_numbers.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["macro", "value", "source"])
        w.writerows((f"\\v{n}", v, s) for n, v, s in MACROS)
    print(f"{len(MACROS)} macros, 4 tables")


if __name__ == "__main__":
    main()
