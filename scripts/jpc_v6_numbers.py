r"""Numbers and condensed tables of the JPC v7 manuscript, generated from the CSV mirrors.

Every value quoted in the main text of Artigo 1 is a LaTeX macro defined here from
`results/jpc/*.csv` (written by `experiments/build_paper_assets.py jpc-remediation`), or from
the plant code for the two steady-state quantities of Proposition 1. Nothing is typed by hand.

Outputs:
    papers/01_journal_of_process_control/generated/numbers.tex   (\\newcommand macros)
    papers/01_journal_of_process_control/tables/v7_*.tex         (condensed tables)
    results/jpc/v7_numbers.csv                                    (macro -> value, source)

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
    header: list[str], body: list[list[str]], caption: str, label: str, group: str = ""
) -> str:
    """Starred booktabs float in the style of exp02.export_latex_table; `group` is an optional top row."""
    top = [group + r" \\"] if group else []
    lines = top + [" & ".join(header) + r" \\", r"\midrule"] + [" & ".join(r) + r" \\" for r in body]
    return (
        "\\begin{table*}[t]\n\\centering\n\\footnotesize\n"
        f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
        f"\\begin{{tabular}}{{l{'c' * (len(header) - 1)}}}\n\\toprule\n"
        + "\n".join(lines)
        + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n"
    )


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
    proposition_numbers()
    latch_check_numbers()
    back_calculation_numbers()
    back_calculation_detail()
    smax_cols, smax_body = regime_map()
    pol, ext_body = robustness_extension()
    tb_body = testbed_table()
    measurement_numbers()
    rate_trigger_numbers()
    predictive_and_exact_numbers()
    load_cols, load_body = load_table()

    tables = PAPER / "tables"
    (tables / "v7_testbed.tex").write_text(
        booktabs(
            [
                "Tuning",
                "\\(K_p\\)",
                "\\(T_i\\) (min)",
                "\\(T_d\\) (min)",
                "IAE",
                "TV (L/min)",
                "\\(M_p\\) (\\%)",
                "\\(M_s^{\\mathrm{FOPTD}}\\)",
                "\\(\\|S\\|_\\infty^{\\mathrm{lin}}\\)",
                "\\(\\|CS\\|_\\infty^{\\mathrm{lin}}\\) (L/min/K)",
            ],
            tb_body,
            "Test-bed loops: gains, nominal $-2$~K step with the directional rule (IAE in K$\\cdot$min), "
            "sensitivity peak on the identified FOPTD and on the exact linearization with the half-sample "
            "hold, and the peak of the noise-to-valve gain $CS = C/(1+L)$, which equals "
            "$|K_p|(1+N)$ to within $0.3$~L/min/K.",
            "tab:testbed",
        ),
        encoding="utf-8",
    )
    (tables / "v7_smax_ratio.tex").write_text(
        booktabs(
            ["Tuning", *smax_cols],
            smax_body,
            "Regime map: IAE of amplitude-only directional clamping over IAE of the rate-aware rule "
            "on the $-2$~K step against the slew limit $S_{\\max}$ (L/min$^2$), gains fixed. Above $1$ the "
            "rate trigger improves the loop; below $1$ it makes the loop worse.",
            "tab:smax_ratio",
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
            ["Tuning", *load_cols],
            load_body,
            "Deterministic rejection of a $+2$~K feed-temperature step at $t = 2$~min and a $+10\\%$ "
            "feed-concentration step at $t = 8$~min ($15$~min, no noise, directional rule).",
            "tab:load",
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
    with open(RES / "v7_numbers.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["macro", "value", "source"])
        w.writerows((f"\\v{n}", v, s) for n, v, s in MACROS)
    print(f"{len(MACROS)} macros, 4 tables")


if __name__ == "__main__":
    main()
