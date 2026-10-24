# WAVE 6 — Coordinator Audit Report

Date: 2026-10-24 · Branch: `main` · Coordinator: Claude (Main Coordinator, Hub-and-Spoke)

## 1. Integration status

| Order | Branch | Tip | Commits | Result |
|---|---|---|---|---|
| 1 | `fix/paper1-jpc-remediation` | `8b5b05a` | 3 (IC-T21, IC-T22) | merged, no conflict (`ec22579`) |
| 2 | `fix/paper2-cce-remediation` | `2ed4c67` | 1 (IC-T23, IC-T24) | merged, no conflict (`4cdf77f`) |
| 3 | `fix/paper3-cerd-remediation` | `2b8cbb5` | 2 (IC-T25, IC-T26) | merged, 1 conflict (`6f244d3`) |

Conflicted file: `tests/test_classical_control.py`. Both sides appended new test classes at end of file
(`TestAntiWindupFactorial` from Paper 1, slave gain-scheduling tests from Paper 3). Resolution: keep both blocks.
`src/` and `experiments/build_paper_assets.py` had no textual conflict.
`.antigravity/TICKETS.md` auto-merged.

A first attempt, earlier in the session, was halted: branch 2 had no commits (work only uncommitted in its worktree).
It was re-run after the branch 2 conversation committed.

## 2. Validation

| Check | Result |
|---|---|
| `ruff check .` | All checks passed |
| `.venv/bin/pytest tests/ -v` | **144 passed, 1 xfailed**, 2 warnings (do-mpc optional ONNX/opcua) — run before and after the IC-T27 edits |
| `make papers` | **target does not exist** in the Makefile; used `make papers-pdf` and `make papers-pack` (includes `desk-check`) |
| LaTeX (final build) | 3 PDFs compile; 0 errors, 0 undefined refs/citations, largest overfull hbox 9.5 pt (≤ 15 pt) |
| Elsevier desk-check | PASSED for all 3 papers |

Overfull boxes fixed during IC-T27 (all introduced by Paper 2 branch equations or by the new CRediT block):
Eq. `disturbance_model` (84.6 pt), `disturbance_update` (75.0 pt), `mhe` (63.8 pt), `ua_crit` (63.8 pt), CRediT line (16.7 pt, Papers 2 and 3).

### IC-T27 — what was done
- Author ORCID `0009-0008-8868-5100` in the three `main.tex` (Paper 3 had an empty `orcid=`).
- Gabriel's CRediT roles unified to the ticket text in all three; explicit "CRediT authorship contribution statement" section added to Papers 1 and 2 (Paper 3 already used `\printcredits`).
- "Declaration of generative AI and AI-assisted technologies" section added to all three (names Claude as coding / language-editing aid). **Author must confirm the wording is accurate before submission.**
- ITAE unit (K·min²) in table headers of Papers 1 and 2 (14 `.tex` files + `ready-to-overleaf` copies) and in the generator column keys of `exp_01`, `exp_01b`, `exp_02`. $M_p$ and $t_s$ (2 % band) defined in the metric paragraph of Papers 1 and 2 Results.
- `ready-to-overleaf` re-synced; zips rebuilt via `make papers-pack`; checksums in `results/overleaf_zips.sha256`:

```
227843a3528636a915bbac457defc7ca27dd56ab04110e74b53517f1e3ec5a52  01_journal_of_process_control/ready_to_overleaf.zip
eba522208bc1ec39c2d69c2e2ec5cec17e9f2445a2c5b84ba82170bb38063896  02_computers_chemical_engineering/ready_to_overleaf.zip
90ad7167d42de9bcc0c87f996f1f50b6dacd9cf7f6fa7ae65f328648bb09655c  03_chemical_engineering_research_design/ready_to_overleaf.zip
```

## 3. Technical checklist per paper

### Paper 1 (JPC) — IC-T21/T22
IAE (K·min) / overshoot (%) on the −2 K step, from `results/jpc/antiwindup_ablation.csv`:

| Tuning | Naive "Textbook" | None | Back-calculation | Directional (proposed) |
|---|---|---|---|---|
| ZN | 104.12 / 842.5 | 91.11 / 631.2 | 0.97 / 25.5 | 0.94 / 22.6 |
| CC | 102.67 / 842.5 | 87.37 / 593.5 | 0.87 / 15.6 | 1.02 / 31.0 |
| AMIGO | 1.60 / 68.6 | 1.60 / 68.6 | 0.92 / 8.0 | 0.93 / 9.7 |
| Optimal ITAE | 1.51 / 66.0 | 1.51 / 66.0 | 0.99 / 0.0 | 0.83 / 2.2 |

- Directional clamping and back-calculation are equivalent in IAE for ZN/CC/AMIGO (within ~0.15 K·min); the naive rule locks the valve at full cooling for ZN/CC (T_min 377.8 K) — mechanism in `antiwindup_mechanism.csv`.
- Plant-exact $\|CS\|_\infty$ (L/min/K): ZN 490.1, CC 559.2, TL 309.0, AMIGO 195.6, SIMC 77.3, Optimal ITAE 258.9; $K_{hf}=|K_p|(1+N)$ matches within 0.2 %.
- Measurement low-pass filter: implemented ($\tau_m = 0.05$ min, exact ZOH discretization, metrics on true T); paired tests with 95 % CI in `noise_filter_paired_tests.csv`; benchmark tables use $\tau_m=0$.

### Paper 2 (CCE) — IC-T23/T24
- Steady-state offset under unmeasured load disturbance (feed T +5 K, C_Af +20 %): NMPC-Oracle (OF) 0.00 K, NMPC-MHE (OF) −0.02 K → **< 0.05 K confirmed** (text and unit test). Original NMPC retains offset.
- $UA_{crit}$ = **63.75 %** of nominal ($T_{sp}$ = 394.65 K, $q_{j,max}$ = 300 L/min); recorded in caption of `ua_critical_table.tex`. The 60 % UA scenario is reframed as physical infeasibility.
- LHS Monte Carlo: N = 28, joblib-parallel, 26/28 converged (2 samples without steady state). Offset-free NMPC-MHE mean IAE 6.41 (P95 8.40), $|e_{ss}|_{max}$ 0.003 K; original: mean IAE 31.25, $|e_{ss}|_{max}$ 12.04 K.
- **CPU time of the IC-T24 LHS campaign: NOT RECORDED.** Neither `exp_07_cce_remediation.py` nor the manuscript logs wall time for the Monte Carlo. Only the per-sample NMPC cost (31.46 ms Oracle / 39.28 ms MHE) is reported. Requires a re-run with timing to fill this item.

### Paper 3 (CERD) — IC-T25/T26
- Hopf bifurcation: at both frozen-UA boundaries the dominant closed-loop pair lies on the imaginary axis (Re λ = 0), Im λ = ±0.76 rad/min (SIMC single loop, UA 89.3 %) and ±0.64 rad/min (cascade, 86.1 %), with $K_c k > 1$ there (≈ 1.5) → instability is dynamic, not loss of static gain. Confirmed by `frozen_ua_stability.csv` and Sec. 4.2.
- $b_3$ at $UA_{crit}$: code and manuscript give **−0.267 K/L** (factor 5.4; `tests/test_cstr_model.py`, `numbers.csv: bThreeCrit`). The ticket text states −0.268; the difference is third-decimal rounding of the same number, not re-derived here. The old value (−0.315, factor 4.6) is gone.
- IAE, scheduled cascade vs optimal SISO (`numbers.csv`): coolant-supply shock 12.72 vs **8.99**; feed-temperature shock 85.63 vs **10.50**. SISO optimal has $M_s$ = 1.59 (≤ 1.60). **The scheduled cascade does not beat the Ms-optimal SISO on these shocks**; its advantage exists only against the SIMC SISO (−88.1 % IAE on the coolant shock, +3.1 % worse on the feed shock). Scheduling does not extend the frozen-UA cascade boundary (86.1 → 85.5 %).

## 4. Regression matrix, known failures and limitations

| Item | Status |
|---|---|
| pytest | 0 failed; 1 xfail: `test_robustness_ms_below_1_65[tune_tyreus_luyben-PID]` (pre-existing; exact TL-PID gives Ms ≈ 2.32; escalated to auditor, formula not altered) |
| IC-T24 LHS CPU time | missing (see above) |
| IC-T27 – not done | merge of redundant tables (Table 2/6 of Paper 1); bibliography modernization 2019–2026; BibTeX/Zenodo-style citation of companion papers (Paper 3 cites them by key `andrade2026robust`, etc.) |
| `make papers` | target absent from Makefile (ticket wording) |
| Table/text rounding | `ua_critical_table.tex` row shows "63.7 %" while caption says 63.75 % (row formatted with one decimal in the stored table; value consistent) |
| ITAE unit fix | applied to existing `.tex` headers and to generator keys, but experiments were **not re-run**; regenerating tables is expected to give identical numbers but was not verified |
| AI disclosure wording | drafted by the coordinator; author must verify |
| `ready-to-overleaf/sections` of Paper 2 | were stale relative to `sections/` on branch 2; re-synced here |
| Tickets file | `TICKETS.md` checkbox state not updated for IC-T23/T24/T27 |
