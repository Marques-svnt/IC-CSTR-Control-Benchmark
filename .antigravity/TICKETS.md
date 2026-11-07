# Ticket Queue — IC (`cstr-control-research`)

> **Instructions for Claude PRO:**
> Wave 1 (`IC-T01` $\to$ `IC-T05`) is complete (`[x]`).
> Execute Wave 2 (`IC-T06` $\to$ `IC-T09`) sequentially to resolve all 7 Major Technical Issues and 4 Editorial Issues from the specialist peer-review audit. Follow strict TDD, run `.venv/bin/pytest -q`, regenerate all tables/figures, and recompile `main.pdf`.

---

## Wave 1 (Completed)
- [x] `IC-T01`: Implement Modern Classical Baselines (Tyreus-Luyben, AMIGO, 2-DOF PID)
- [x] `IC-T02`: Fix Critical Bugs in `tuning_optimization.py`, `metrics.py`, and `exp_02_robustness_campaign.py`
- [x] `IC-T03`: Align NMPC Oracle + MHE Output-Feedback & Add Sobol Sensitivity (`SALib`)
- [x] `IC-T04`: Re-run Experimental Campaigns & Regenerate Publication Figures (`tueplots` + `adjustText`)
- [x] `IC-T05`: Upgrade IC Article 1 Manuscript to Q1 Standard & Compile Clean PDF

---

## Wave 2 — Peer-Review Audit Remediation (`70.6/100` $\to$ `>92/100` Qualis A1)

## [x] `IC-T06`: Fix Anti-Windup Slew-Rate/Sign Bug, True-State `IAE`, & Step-Time Alignment (`metrics.py`, `pid_controller.py`, `closed_loop.py`)
- **Files:**
  - `src/classical_control/pid_controller.py`
  - `src/classical_control/closed_loop.py`
  - `src/evaluation/metrics.py`
  - `tests/test_classical_control.py`
  - `tests/test_metrics.py`
- **Requirements:**
  1. **Slew-Rate & Sign-Correct Clamping Anti-Windup (`src/classical_control/pid_controller.py:235-241`):**
     - Replace the flawed amplitude-only check (`if self._last_u_unconstrained >= self.limits.u_max and error > 0.0`) with the exact directional saturation condition covering **both** position limits $[u_{\min}, u_{\max}]$ and velocity limits $|du/dt| \le S_{\max}$ with the correct sign of `i_gain = self.gains.kp / self.gains.ti`:
       ```python
       if self.anti_windup == AntiWindupMethod.CLAMPING and self._is_saturated:
           sat_excess = self._last_u_unconstrained - self._last_u_applied
           if sat_excess * (i_gain * error) > 0.0:
               should_integrate = False
       ```
  2. **True-State `IAE` Evaluation (`src/classical_control/closed_loop.py:156-162`):**
     - Pass `y=states[:, 1]` (the true physical reactor temperature $T_{\text{true}}(t)$) instead of `y=t_pv_arr` (noisy sensor reading) into `evaluate_performance(...)` so that measurement noise $\eta(t)$ is not integrated into $\mathrm{IAE}$, $\mathrm{ITAE}$, $\mathrm{ISE}$, $M_p$, and $t_s$.
  3. **Step-Time Shifted `ITAE` (`src/evaluation/metrics.py`):**
     - Add `t_step: float = 0.0` to `evaluate_performance()` and compute `t_rel = np.maximum(0.0, t - t_step)` so $\mathrm{ITAE} = \int \max(0, t - t_{\text{step}})|e(t)|\,dt$.
- **Acceptance Criteria:**
  - Unit tests in `tests/test_classical_control.py` and `tests/test_metrics.py` verify: (a) integrator freezes during a slew-rate-limited cooling ramp when $K_p < 0$ and $e_k < 0$; (b) `evaluate_performance` with `t_step=0.5` has zero pre-step ITAE inflation; (c) `ClosedLoopSimulator.run` computes `metrics.iae` against `states[:, 1]`.

---

## [x] `IC-T07`: Fix `NMPC-Oracle` Noise Leak & `NMPC-MHE` Zero-Noise Trajectory Equivalence (`nmpc_controller.py`)
- **Blocked by:** `IC-T06`
- **Files:**
  - `src/controllers/optimal/nmpc_controller.py`
  - `tests/test_sobol_and_nmpc.py`
- **Requirements:**
  1. **Eliminate Sensor Noise Leak in `NMPC-Oracle` (`src/controllers/optimal/nmpc_controller.py:471-520`):**
     - Add `true_alpha_ua: float = 1.0` attribute to `CstrNmpcController`.
     - When `self.feedback_mode == "oracle"`, NEVER feed the noisy `measurement` into `self.estimator.step()`. Instead, use the noise-free `full_state` (`c_a, t, t_j = float(full_state[0]), float(full_state[1]), float(full_state[2])`) and `self._estimated_alpha_ua = self.true_alpha_ua` (or if estimating `alpha_ua` under deterministic fouling, pass `t_meas=float(full_state[1]), t_j_meas=float(full_state[2])` from the noise-free `full_state`).
     - Verify with a test in `tests/test_sobol_and_nmpc.py` that `NMPC-Oracle` produces **bit-for-bit identical** `u_applied`, `IAE`, and `TV` for `noise_std=0.0` and `noise_std=1.0` (`std = 0.0`).
  2. **Zero-Noise Equivalence of `NMPC-MHE` and `NMPC-Oracle` (`src/controllers/optimal/nmpc_controller.py:148-237`):**
     - In `AugmentedCstrStateEstimator`, replace the 1-step RK2 prediction with the exact 4-substep **RK4** integration matching `CstrNmpcController._build_model()`.
     - In `mhe_residual(theta)`, instead of holding `ca_curr` constant across all $N_m = 8$ steps of the window during a transient, forward-propagate the state vector $[C_A, T, T_j]$ from the start of the window using RK4 with parameter `alpha_curr`. Consequently, on the nominal noise-free plant ($\sigma = 0, \alpha_{UA} = 1.0$), the innovation and window residual vanish identically, and `NMPC-MHE` reproduces the `NMPC-Oracle` nominal trajectory and `TV`!
- **Acceptance Criteria:**
  - `pytest tests/test_sobol_and_nmpc.py` verifies: (1) `NMPC-Oracle` `TV` and `IAE` are invariant to `noise_std`; (2) at `noise_std=0.0` and nominal $100\%\text{ UA}$, `NMPC-MHE` and `NMPC-Oracle` match within $< 1\%$ on `IAE` and `TV`.

---

## [x] `IC-T08`: Unify Campaign Step Protocols, Add `2-DOF AMIGO`, & Tune Cascade via Sequential SIMC (`experiments/`)
- **Blocked by:** `IC-T06`, `IC-T07`
- **Files:**
  - `experiments/exp_01_classical_benchmark.py`
  - `experiments/exp_02_robustness_campaign.py`
  - `experiments/exp_05_cascade_benchmark.py`
- **Requirements:**
  1. **Unify Servo Step Protocol Across Table 2, Table 4 ($100\%\text{ UA}$), and Table 6 ($\sigma = 0.0\text{ K}$):**
     - Ensure `exp_01_classical_benchmark.py` (Table 2), `run_fouling_campaign` in `exp_02_robustness_campaign.py` (Table 4 at $100\%\text{ UA}$), and `run_noise_and_pareto_campaign` in `exp_02_robustness_campaign.py` (Table 6 at $\sigma = 0.0\text{ K}$) use the **exact same** `t_span`, `setpoint_func`, and `t_step` so that the $100\%\text{ UA}$ rows of Table 4 and the $\sigma = 0.0\text{ K}$ rows of Table 6 match Table 2 **identically**.
  2. **Add `2-DOF AMIGO` (`experiments/exp_02_robustness_campaign.py:120-129`):**
     - Add `"2-DOF AMIGO": replace(amigo_gains, beta=0.5, gamma=0.0)` to `setup_controllers()` so AMIGO is evaluated fairly with 2-DOF setpoint weighting alongside 1-DOF AMIGO and 2-DOF Optimal ITAE.
  3. **Sequential Skogestad SIMC Cascade Tuning (`experiments/exp_05_cascade_benchmark.py:65-72`):**
     - Replace the arbitrary cascade gains (`kp=2.2, ti=0.8` / `kp=-6.0, ti=0.12`) with the analytical Sequential Skogestad SIMC gains derived in `.antigravity/SPEC.md` §2.7:
       - Slave loop ($\tau_{c2} = 0.10\text{ min}$): `PIDGains(kp=-3.45, ti=0.10, td=0.0)`
       - Master loop ($\tau_{c1} = 0.40\text{ min}$): `PIDGains(kp=1.61, ti=0.643, td=0.040, n_filter=10.0)`
  4. Re-run `exp_01_classical_benchmark.py`, `exp_02_robustness_campaign.py`, `exp_03_pareto_tuning_sweep.py`, `exp_04_neural_control_benchmark.py`, `exp_05_cascade_benchmark.py`, and `generate_maximum_paper_figures.py` to regenerate all `.csv`, `.tex` tables, and `.pdf` figures.
- **Acceptance Criteria:**
  - All tables in `overleaf/tables/` and `results/*.csv` are regenerated; Table 2, Table 4 ($100\%\text{ UA}$), and Table 6 ($\sigma = 0.0\text{ K}$) have identical numbers; `NMPC-Oracle` has constant `TV` across all $\sigma$ in Table 6; Cascade response in `fig6_cascade_comparison.pdf` (Figure 9) is smooth and well-damped.

---

## [x] `IC-T09`: Resolve All Manuscript Technical & Editorial Audit Items (`overleaf/sections/*.tex`) & Compile Clean PDF
- **Blocked by:** `IC-T08`
- **Files:**
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/02_modeling.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/03_pid_classical.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/04_results.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/05_conclusion.tex`
- **Requirements:**
  1. **Section 2 (`02_modeling.tex`):**
     - Line 78: Move the inline steady-state jacket equation $T_j(q_j, T) = \frac{q_j T_{jf} + (UA/\rho_j C_{pj})T}{q_j + UA/\rho_j C_{pj}}$ into a proper numbered `equation` environment.
     - Line 94: Replace raw Markdown `**locally asymptotically stable in open loop**` with `\textbf{locally asymptotically stable in open loop}` (check all `.tex` files for any remaining `**`!).
     - Lines 99-103 (Eq. 14): Format the Jacobian matrix $\mathbf{A}$ with `\setlength{\arraycolsep}{6pt}` so `-19.923` and `-0.0528` do not touch.
  2. **Section 3 (`03_pid_classical.tex`):**
     - Equation (21) (lines 24-29): Update the anti-windup clamping law to explicitly show directional saturation covering both amplitude and slew-rate limits: $(u_{\text{raw},k-1} - u_{\text{act},k-1})(K_p e_k) > 0$.
     - Section 3.4 & 3.5: Discuss `2-DOF AMIGO` ($\beta = 0.5, \gamma = 0$) and explain why constrained Nelder-Mead (`Optimal ITAE`) converges to $T_d = 0.000\text{ min}$ (a pure PI controller with $M_s = 1.22 < 1.60$) on this lag-dominant, slew-rate-constrained process.
     - Equation (32) (line 108): Fix spacing between $e_p$, $e_i$, and $e_d$.
     - Section 3.6: Write out the explicit mathematical equations of the 4-state Augmented EKF + Moving Horizon estimator ($\mathbf{x}_a = [C_A, T, T_j, \alpha_{UA}]^\top$, $\dot{\alpha}_{UA} = 0$, $Q_e, R_e, P_0$).
     - Section 3.9: Present the Sequential Skogestad SIMC derivation for the Master ($K_{p1}=1.61, T_{i1}=0.643, T_{d1}=0.040$) and Slave ($K_{p2}=-3.45, T_{i2}=0.10$) cascade loops.
  3. **Section 4 & 5 (`04_results.tex`, `05_conclusion.tex`):**
     - Synchronize every number cited in the text with the regenerated tables from `IC-T08`.
     - Explain clearly the Fouling initialization protocol in Section 4.3, the true-state $\mathrm{IAE}_{\text{true}}$ evaluation in Section 4.5, and the invariance of `NMPC-Oracle` to sensor noise in Table 6.
     - Fix Table 10 column spacing (`\tabcolsep`) so `Total TV (L/min)` and `Max Valve (L/min)` do not collide.
  4. Compile `main.tex` via `pdflatex` + `bibtex` + `pdflatex` $\times 2$ and verify 0 errors, 0 undefined references, and 0 raw `**` tokens.
- **Acceptance Criteria:**
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/main.pdf` compiles cleanly with all 7 Major Issues and 4 Minor Issues resolved.


---

## Wave 3 — Peer-Review Hardening & Final Qualis A1 Polish (`>95/100`)

> **Instructions for Claude PRO:**
> `IC-T10` has already been implemented by Antigravity in code and manuscript text.
> Your task is to execute `IC-T11` (compile and verify clean LaTeX/PDF text layer) and `IC-T12` (re-run timing benchmark when CPU is quiescent, run full pytest suite, and sync Obsidian).

---

## [x] `IC-T10`: Implement Priorities P1–P7 from Specialist Peer-Review Refinement Guide
- **Status:** Completed by Antigravity.
- **Files Modified:**
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/main.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/02_modeling.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/03_pid_classical.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/04_results.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/05_conclusion.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/tables/nmpc_oracle_benchmark.tex`
  - `experiments/exp_01b_nmpc_oracle_comparison.py`
  - `src/classical_control/pid_controller.py`
- **Accomplishments:**
  1. **P1 ($T_{j,\min}(T)$ Display Equation):** Promoted $T_{j,\min}(T) = \frac{u_{\max} T_{jf} + (UA/\rho_j C_{pj})T}{u_{\max} + UA/\rho_j C_{pj}} > T_{jf}$ from inline nested fraction to numbered display equation (Eq. 18 in `02_modeling.tex`), ensuring clean PDF text-layer extraction.
  2. **P2 (Exact $G_{\text{true}}(s)$ Relative Degree 2 Damping):** Formulated exact transfer function $G_{\text{true}}(s) = \mathbf{C}(s\mathbf{I}-\mathbf{A})^{-1}\mathbf{B} = \frac{-2.416(s+19.923)}{(s+1.5712)(s+11.8006)(s+13.2693)}$ in Section 3.3 (`03_pid_classical.tex:49-58`). Explained why ZN ($M_s=4.14$) and CC ($M_s=4.54$) do not oscillate on the delay-free ODE: relative degree 2 produces asymptotic $-180^\circ$ phase, derivative lead pushes phase to $-90^\circ$, and valve rate limiting ($80\text{ L/min}^2$) + rate-aware clamping turns proportional spikes into bounded ramps. Cross-referenced in Section 4.2 (`04_results.tex:32`) and Section 5 (`05_conclusion.tex:7`).
  3. **P3 (Cascade Inner-to-Outer Coupling & Gain Conservatism):** Formulated exact closed-inner-loop $2\times 2$ sub-block $\mathbf{A}_{12}$ dynamics ($\det(s\mathbf{I}-\mathbf{A}_{12}) = s^2 + 16.641s + 34.432 = (s+2.426)(s+14.215)$) in Section 3.9 (`03_pid_classical.tex:198`), proving that the open-loop ratio approximation ($K_1 = 0.766, \tau_1 = 0.643$) overestimates the exact sub-block gain ($K_{1,\text{exact}} = 0.579, \tau_{1,\text{exact}} = 0.412$) by $32\%$, intentionally prescribing a conservative master gain $K_{p1}=1.61$ that enhances robustness margins against rate saturation.
  4. **P4 (EKF+MHE Arrival-Cost Indexing & Forward Propagation):** Updated Eq. (36) in `03_pid_classical.tex:135-140` with explicit arrival cost priors $(\hat{C}_{A,k-N_m+1}^{\text{prior}}, \hat{\alpha}_{UA,k-N_m+1}^{\text{prior}})$ at the window start, and documented forward chaining of $\mathbf{F}$ across the $N_m-1$ window steps to compute terminal estimate $\hat{\mathbf{x}}_{a,k}$.
  5. **P5 (1-DOF Optimal ITAE in Table 7 & Quantitative Anti-Windup Ablation):**
     - Added 1-DOF `Optimal ITAE ($M_s \le 1.6$)` to `COMPARED` in `experiments/exp_01b_nmpc_oracle_comparison.py`, simulated, and regenerated `tables/nmpc_oracle_benchmark.tex` and `figures/fig_nmpc_oracle_comparison.pdf`/`.png`.
     - Synchronized Section 4.7, Section 4.10, Section 5, and Abstract: NMPC-Oracle reduces IAE of best PID (AMIGO) by $21.0\%$ ($5.474$ vs $6.927\text{ K}\cdot\text{min}$) and 1-DOF Optimal ITAE by $25.1\%$ ($7.312\text{ K}\cdot\text{min}$).
     - Documented exact ablation values for naive sign-blind amplitude-only clamping in Section 4.2: ZN reaches $\mathrm{IAE} = 104.12\text{ K}\cdot\text{min}$ ($M_p = 845.3\%$, $\mathrm{TV} = 480.8\text{ L/min}$) and CC reaches $\mathrm{IAE} = 107.12\text{ K}\cdot\text{min}$ ($M_p = 861.4\%$, $\mathrm{TV} = 472.7\text{ L/min}$).
  6. **P6 (Trapezoidal Consistency for Clamping Anti-Windup):** Aligned conditional integration in `src/classical_control/pid_controller.py:233-245` with trapezoidal increment $e_{\text{trap}} = 0.5(e_k + e_{k-1})$ in both the saturation excess check and the integral update. Explained $(u_{\text{raw},k-1} - u_{\text{act},k-1})$ single-sample delay in Eq. (22) of `03_pid_classical.tex` to eliminate implicit algebraic loops.
  7. **P7 (Typography & Unit Hygiene):** Replaced `(*stiction*)` with `(\emph{stiction})` in `02_modeling.tex:37`, formatted Table 1 units with explicit center dots $\text{cal}/(\text{L}\cdot\text{K})$ and $\text{cal}/(\text{min}\cdot\text{K})$, and verified zero label collision in Figure 5(a) (`fig4_pareto_iae_tv.png`).

---

## [x] `IC-T11`: Recompile Manuscript PDF & Verify Clean Text Layer
- **Blocked by:** `IC-T10`
- **Files:**
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/main.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/main.pdf`
- **Requirements:**
  1. In directory `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/`, compile `main.tex`:
     ```bash
     pdflatex -interaction=nonstopmode main.tex
     bibtex main
     pdflatex -interaction=nonstopmode main.tex
     pdflatex -interaction=nonstopmode main.tex
     ```
  2. Verify 0 fatal errors, 0 undefined references (`?`), 0 missing citations, and 0 overfull hboxes $> 15\text{ pt}$.
  3. Extract text from pages 5–10 using `pdftotext -f 5 -l 10 main.pdf -` and verify:
     - Equation (18) for $T_{j,\min}(T)$ extracts as a clean standalone equation without split fractions.
     - Table 1 units display with explicit center dots (`cal/(L·K)`).
     - No raw Markdown asterisks (`*stiction*` or `**`) exist in the text layer.
- **Acceptance Criteria:**
  - `main.pdf` compiles cleanly and all equations/tables in the text layer match publication standards.

---

## [x] `IC-T12`: Quiescent Timing Refresh for Table 7, Full Pytest Execution, & Obsidian Sync
- **Blocked by:** `IC-T11`, TCC background FEA completion
- **Files:**
  - `experiments/exp_01b_nmpc_oracle_comparison.py`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/tables/nmpc_oracle_benchmark.tex`
  - `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/sections/04_results.tex`
- **Requirements:**
  1. Once TCC background tasks complete (CPU at quiescent load $< 20\%$), re-run:
     ```bash
     .venv/bin/python experiments/exp_01b_nmpc_oracle_comparison.py
     ```
     Verify that `Step time (ms)` in `tables/nmpc_oracle_benchmark.tex` returns to nominal values ($\approx 33\text{ ms}$ for Oracle, $\approx 39\text{ ms}$ for MHE).
  2. Run the complete pytest test suite:
     ```bash
     .venv/bin/pytest -q
     ```
     Verify that all 100 tests pass (with 1 expected xfail on TL-PID).
  3. Sincronize with the Obsidian vault (Second Brain):
     ```bash
     python3 /home/marques/vault/svnt/scripts/sync_antigravity.py
     ```
     Verify that `00-Dashboard/Antigravity-Sync-Index.md` is updated.
- **Acceptance Criteria:**
  - Table 7 step times reflect quiescent hardware, test suite is 100% green, and Obsidian vault is in sync.

---

## Execution Report — `IC-T11` / `IC-T12` + Full Regeneration (Claude Code, 2026-10-18)
- **Status:** `IC-T11` and `IC-T12` completed. In addition, **all campaigns were regenerated** after a code-version mismatch was found (see §2). Every table, CSV, figure and the PDF now come from the current code.

### 1. `IC-T11` / `IC-T12` outcomes
- `main.pdf`: 37 pages, 0 LaTeX errors, 0 undefined references/citations, 0 overfull hboxes, 0 BibTeX warnings.
- Eq. (18): with `\frac` the PDF text layer split numerator/denominator onto separate lines. Rewritten as a one-line slash form `T_{j,min}(T) = [u_max T_jf + (UA/ρ_j C_pj) T] / [u_max + UA/ρ_j C_pj] > T_jf` (`02_modeling.tex`); `pdftotext` now extracts it on one line. Same mathematics.
- Table 1 renders `cal/(L · K)`. No raw Markdown asterisks in sources or PDF; the only 3 `*` in the text layer are the `sn-jnl` `\author*` corresponding-author markers (intended).
- Table 7 step time at quiescent CPU (load < 2.4 / 12 cores): **32.70 ms (Oracle), 39.21 ms (MHE)**, PID 0.09 ms.
- `pytest`: **107 passed, 1 xfailed** (TL-PID Ms = 2.32, strict xfail). The ticket's "100 tests" count is outdated.
- Obsidian: `sync_antigravity.py` ran OK (126 artifacts, `00-Dashboard/Antigravity-Sync-Index.md` updated). Note: it ran *before* the regeneration in §2; the sync indexes Antigravity brain files, not `results/`, so no re-run is needed for the numbers.

### 2. Root cause of the Table 7 number drift (investigated and confirmed)
- `IC-T10` P6 changed the clamping freeze condition in `src/classical_control/pid_controller.py` (11:11) from `sat_excess * (i_gain * error) > 0` to `sat_excess * (i_gain * e_trap) > 0` with `e_trap = 0.5 (e_k + e_{k-1})`. Eq. (21) in `03_pid_classical.tex` was updated consistently.
- Both rules differ only when the error changes sign while the valve is saturated (frequent under sensor noise). Reproduced exactly: with the old rule Table 7 PID rows are AMIGO 6.927 / SIMC 12.483 / Opt-ITAE 7.312 / 2-DOF 7.707; with the current rule 6.932 / 12.485 / 7.320 / 7.708.
- **Problem found:** only Table 7 had been regenerated after 11:11. All other tables (nominal, disturbance, fouling, noise MC, multi-step, Pareto, Sobol, cascade) still came from the old rule, i.e. the manuscript mixed two code versions.

### 3. Fix: full regeneration with the current rule
- Re-ran `exp_01`, `exp_01b`, `exp_02` (incl. Monte Carlo and Sobol N = 512), `exp_03` (cache deleted), `exp_05`, `exp_04`.
- Changes are at the 2nd–3rd decimal, concentrated on saturating tunings (ZN, CC, AMIGO, TL) and noisy campaigns. Largest: noise MC at σ = 1 K, ZN 8.42 → 7.45, CC 7.53 → 7.03, Optimal ITAE 4.31 → 4.16, SIMC 3.47 → 3.56. Nominal noise-free: only ZN/CC TV change (82.0 → 81.9, 104.2 → 104.0).
- **No qualitative conclusion changed** (SIMC still the lowest-error PID under heavy noise; NMPC gains unchanged: 21.0 % vs AMIGO after fouling, 2.3 % nominal vs Optimal ITAE, 2.5 % wide-range vs AMIGO).
- Prose re-synchronized: 16 edits in `04_results.tex`, 1 in `05_conclusion.tex`; abstract unaffected. Also updated values introduced by `IC-T10` P5 (Table 7: AMIGO 6.932, +26.6 %; Opt-ITAE 7.320, +33.7 %, reduction 25.2 %).

### 4. Verification
- Every row of every `results/<table>.csv` appears identically in `overleaf/tables/<table>.tex`: **172 rows, 0 mismatches**.
- Automated scan: no decimal number in `04_results.tex`, `05_conclusion.tex`, `03_pid_classical.tex` or the abstract that existed only in the pre-regeneration tables (the only hit, `2.6`, is the derived Ms ratio 4.14/1.60, unchanged).
- `ruff check .` clean; `pytest` 107 passed, 1 xfailed.

### 5. Open items for the orchestrator
- **Unverifiable numbers:** the anti-windup ablation values cited in Section 4.2 by `IC-T10` P5 (ZN: IAE = 104.12, Mp = 845.3 %, TV = 480.8; CC: IAE = 107.12, Mp = 861.4 %, TV = 472.7) are not produced by any script in `experiments/`, so they were not regenerated and violate the single-source rule. Recommend a scripted ablation (e.g. an `AntiWindupMethod` variant for the naive rule) that writes a table/CSV.
- `generate_maximum_paper_figures.py` and `generate_fig4_springer.py` are obsolete (4-controller layout) and were not run; running them would overwrite the current figures.
- Per user request, Fig. 5(a) (Pareto) no longer has in-plot adjustText labels; tunings are identified by marker in the legend only.

---

## Wave 4 — Elsevier Modularization & Journal Splitting (`IC-T13` $\to$ `IC-T16`)

> **Instructions for Claude PRO:**
> Execute Wave 4 to split the monolithic 37-page CSTR manuscript into three dedicated Qualis A1 Elsevier publications following the advisor's approved directive.
> All three publications must use the official Elsevier two-column template (`cas-dc.cls`).
> Enforce strict single-source data integrity against `results/*.csv` and `overleaf/tables/`.

---

### [x] `IC-T13`: Scaffold Directories & Elsevier `cas-dc` Environments for the 3 Target Journals
- **Files:**
  - `Artigos_Rascunhos/01_Journal_of_Process_Control/`
  - `Artigos_Rascunhos/02_Computers_Chemical_Engineering/`
  - `Artigos_Rascunhos/03_Chemical_Engineering_Research_Design/`
- **Requirements:**
  1. Create the three target journal directories under `Artigos_Rascunhos/`.
  2. In each directory, scaffold a clean `main.tex` based on `cas-dc.cls` (found in TeX Live or vendor from `/usr/share/texlive/texmf-dist/tex/latex/els-cas-templates/`), with:
     - Documentclass: `\documentclass[a4paper,fleqn]{cas-dc}`
     - Natbib citation management with `\bibliographystyle{elsarticle-num}`.
     - Subdirectories: `sections/`, `figures/`, `tables/`.
     - Copy actual figure PDFs (NO symlinks) from `Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf/figures/`.
     - Copy the clean `references.bib` from `overleaf/references.bib`.
     - Vendor `cas-dc.cls` and `cas-common.sty` directly into the directory to guarantee stand-alone compilation on Overleaf.
     - Authors and Affiliations configured: Gabriel Marques de Andrade and Elilton Rodrigues Edwards (DCET / UESC).
- **Acceptance Criteria:**
  - `pdflatex main.tex` compiles a clean minimal skeleton in all 3 directories with 0 errors.

---

### [x] `IC-T14`: Modularize, Package & Compile Artigo 1: *Journal of Process Control* (`01_Journal_of_Process_Control/`)
- **Blocked by:** `IC-T13`
- **Target Journal:** *Journal of Process Control* (Elsevier, Q1)
- **Title:** *Robust PID Tuning under Actuator Saturation in Nonlinear Exothermic CSTRs: Performance, Anti-Windup and Sensitivity Trade-offs*
- **Requirements:**
  1. **Scope Isolation:**
     - Include exclusively the 8 PID tunings: Ziegler-Nichols, Cohen-Coon, Tyreus-Luyben, AMIGO, 2-DOF AMIGO, Skogestad SIMC, Optimal ITAE ($M_s \le 1.6$), 2-DOF Optimal ITAE.
     - Include directional rate-aware anti-windup (Eq. 23), Pareto continuous frontier (Fig. 5), 1500 Monte Carlo noise realizations (Fig. 6), and Sobol Global Sensitivity Analysis (Fig. 8).
     - **Completely purge all NMPC-Oracle and NMPC-MHE discussion, equations, and tables** from Artigo 1.
  2. **Structure & Content:**
     - `highlights.tex`: 4 bullet points, each strictly $\le 85$ characters (including spaces).
     - `Abstract`: 180–220 words emphasizing the physical controllability limit and directional anti-windup under slew-rate saturation.
     - Sections:
       - `01_introduction.tex`: Focus on the historical failure of empirical rules and the modern relevance of AMIGO/SIMC under hard actuator dynamics.
       - `02_modeling_actuator.tex`: 3-state CSTR model, Van Heerden condition, and valve amplitude/slew-rate dynamics ($80\text{ L/min}^2$).
       - `03_robust_pid_antiwindup.tex`: The 8 tuning rules, dead-time identification ($r=0.1455$), directional clamping rule, and 2-DOF setpoint weighting.
       - `04_results_discussion.tex`: Tables 1, 2, 3, 5, 6, 8; Figures 1, 2, 3, 5, 6, 8.
       - `05_conclusion.tex`: Core conclusions on anti-windup, Pareto frontier, and Sobol variance decomposition.
  3. **Ready-to-Overleaf Export Packaging:**
     - Create a self-contained subdirectory `ready-to-overleaf/` and generate `ready_to_overleaf.zip` containing ONLY:
       - `main.tex`, `highlights.tex`, `references.bib`
       - `sections/*.tex`, `tables/*.tex`
       - `figures/*.pdf` (actual PDF files, NO relative symlinks)
       - `cas-dc.cls` and `cas-common.sty`
       - Exclude all build artifacts (`.aux`, `.log`, `.out`, `.fls`, `.fdb_latexmk`, `.bbl`, `.blg`).
  4. **Verification & Formatting:**
     - Compile via `pdflatex` + `bibtex` + `pdflatex` $\times 2$.
     - Verify page count: strictly between **10 and 14 pages** in `cas-dc`.
     - Verify 0 LaTeX errors, 0 undefined citations/references (`??`), 0 overfull hboxes $> 15\text{ pt}$.
- **Acceptance Criteria:**
  - `01_Journal_of_Process_Control/main.pdf` compiles cleanly, satisfies all Elsevier guidelines, contains no NMPC mentions, and `ready_to_overleaf.zip` is ready for one-click upload to Overleaf.

---

### [x] `IC-T15`: Modularize & Compile Artigo 2: *Computers & Chemical Engineering* (`02_Computers_Chemical_Engineering/`)
- **Blocked by:** `IC-T13`
- **Target Journal:** *Computers & Chemical Engineering* (Elsevier, Q1)
- **Title:** *When Does Nonlinear Model Predictive Control Outperform Robust PID? A Comparative Study under Fouling and Actuator Constraints*
- **Requirements:**
  1. **Scope Isolation:**
     - Benchmark the NMPC-Oracle and NMPC-MHE against the **best linear baselines only** (AMIGO and 1-DOF Optimal ITAE $M_s \le 1.6$).
     - **Completely purge empirical strawmen (Ziegler-Nichols and Cohen-Coon)** from Artigo 2.
  2. **Structure & Content:**
     - `highlights.tex`: 4 bullet points ($\le 85$ chars) highlighting the 2.3% nominal gain vs 21.0% fouling gain and the unmeasured disturbance offset limitation.
     - `Abstract`: 180–220 words addressing the central question: when does the computational overhead of NMPC pay off in non-linear reactors?
     - Sections:
       - `01_introduction.tex`: Critique of unfair non-linear benchmarks vs strawmen; need for comparison against robustly tuned linear baselines under actuator constraints.
       - `02_nmpc_mhe_formulation.tex`: IPOPT/CasADi zero-order hold RK4 map, augmented state $\mathbf{x}_a = [C_A, T, T_j, \alpha_{\text{UA}}]^T$, EKF arrival-cost priors, and moving horizon refinement.
       - `03_baseline_controllers.tex`: Compact summary of AMIGO and 1-DOF Optimal ITAE with directional rate-aware clamping.
       - `04_results_discussion.tex`: Tables 4, 7, 10; Figures 4, 7, 10. Explicit execution time breakdown (32.7 ms Oracle vs 39.2 ms MHE vs 0.09 ms PID).
       - `05_conclusion.tex`: The 5 fundamental criteria delimiting nonlinear control payoff (Section 4.11 of base manuscript).
  3. **Verification & Formatting:**
     - Compile via `pdflatex` + `bibtex` + `pdflatex` $\times 2$.
     - Verify page count: strictly between **10 and 13 pages** in `cas-dc`.
     - Verify 0 LaTeX errors, 0 undefined citations/references (`??`), 0 overfull hboxes $> 15\text{ pt}$.
- **Acceptance Criteria:**
  - `02_Computers_Chemical_Engineering/main.pdf` compiles cleanly, satisfies CACE standards, and presents a razor-sharp NMPC vs robust PID duel.

---

### [x] `IC-T16`: Computational Simulation & Manuscript Scaffolding for Artigo 3: *ChERD* (`03_Chemical_Engineering_Research_Design/`)
- **Blocked by:** `IC-T13`
- **Target Journal:** *Chemical Engineering Research and Design* (Elsevier / IChemE, Q1)
- **Title:** *Thermal Controllability Limits and Cascade Control in Exothermic CSTRs under Cooling Capacity Degradation*
- **Requirements:**
  1. **New Simulation Campaign (`experiments/exp_06_unstable_saddle_and_fouling.py`):**
     - Script the CSTR operation inside the metastable unstable window ($T = 345.0\text{ K}$, where open-loop eigenvalue $\lambda_1 > 0$).
     - Implement Skogestad SIMC rules for unstable lag-dominant plants ($\tau_c < \tau_u - \theta$).
     - Simulate closed-loop response for SISO SIMC vs. Sequential SIMC Cascade under cooling utility shocks ($\Delta T_{jf} = +10\text{ K}$) and feed shocks ($\Delta T_f$).
     - Implement continuous dynamic fouling kinetics:
       $$\frac{d(UA)}{dt} = -\kappa_{\text{foul}} \cdot r_A(C_A, T) \cdot (UA - UA_{\min})$$
       and compute the critical time-to-runaway ($t_{\text{runaway}}$) where the valve saturates at $u_{\max} = 300\text{ L/min}$.
  2. **Manuscript Drafting:**
     - Draft `03_Chemical_Engineering_Research_Design/main.tex` with:
       - Van Heerden stability analysis and steady-state multiplicity (Uppal, Ray & Poore phase portraits).
       - Derivation of the exact closed-inner-loop sub-block $\mathbf{A}_{12}$ and gain overestimation.
       - Cascade control with feedforward utility disturbance rejection.
       - Comparison of SISO vs Cascade on the unstable saddle point.
       - Thermodynamic limit proof ($Q_g > Q_{r,\max}$ at $55\%\text{ UA}$).
  3. **Verification:**
     - Unit tests in `tests/test_cascade_and_unstable.py` verify unstable saddle pole stabilization and dynamic fouling solver stability.
     - Compile initial draft of Artigo 3 in `cas-dc` (10–14 pages).
- **Acceptance Criteria:**
  - `exp_06_unstable_saddle_and_fouling.py` runs cleanly, outputs CSV/figures; `03_Chemical_Engineering_Research_Design/main.pdf` compiles with 0 errors.

---

## Execution Report — Wave 4 (`IC-T13` → `IC-T16`) (Claude Code, 2026-10-22)
- **Status:** all four tickets completed and verified by the parent session before marking `[x]`. `IC-T13`/`IC-T14` executed in the parent session; `IC-T15` and `IC-T16` in parallel sessions (same checkout, disjoint folders), then independently re-checked.
- **Global verification:** `pytest` 124 passed, 1 xfailed (pre-existing TL-PID strict xfail); `ruff check .` clean.

### 1. Shared infrastructure (new)
- `experiments/build_paper_assets.py` builds each paper's tables/figures from the validated runs. It overrides two globals of `exp_02_robustness_campaign.py` before running anything: `RESULTS_DIR = results/<paper>/` (CSV mirrors of the paper tables; **`results/*.csv` of the base manuscript are never overwritten**) and `TABLE_FLOAT_ENV = "table*"` (cas-dc two-column floats; default stays `tableorg` for the base sn-jnl manuscript).
- `run_benchmark` (`exp_01`) now takes `figures_dir`, `tables_dir`, `include_nmpc` (defaults unchanged). The load-disturbance table adds the `alpha_UA_hat` column and its caption sentence only when an NMPC is present.
- New `AntiWindupMethod.CLAMPING_NAIVE` (ablation only: amplitude-only, sign-blind textbook rule), with tests.

### 2. `IC-T13` — scaffolding
- `Artigos_Rascunhos/01_Journal_of_Process_Control/`, `02_Computers_Chemical_Engineering/`, `03_Chemical_Engineering_Research_Design/`: `main.tex` on `\documentclass[a4paper,fleqn]{cas-dc}`, natbib + `elsarticle-num`, authors/affiliation (DCET/UESC), `highlights.tex`, vendored `cas-dc.cls`/`cas-common.sty` (real files), `references.bib`, `sections/ tables/ figures/`. Skeletons compiled with 0 errors.

### 3. `IC-T14` — Artigo 1 (JPC)
- `01_Journal_of_Process_Control/main.pdf`: **12 pages** (cas-dc highlights page + 11 article pages), 0 errors, 0 undefined refs/citations, 0 BibTeX warnings, no `??`, **0 NMPC mentions** in text, tables and figures. `ready_to_overleaf.zip` (27 files, no symlinks, no build artifacts) compiles identically when extracted to a clean folder.
- Highlights 78/77/75/79 characters; abstract 212 words.
- Data integrity: figures/tables that contained NMPC (nominal, load disturbance, noise MC) were **re-run PID-only** (deterministic); Pareto and Sobol tables re-rendered from `results/*.csv`. All 96 PID rows in `results/jpc/*.csv` are identical to `results/*.csv`. Every decimal in the prose was checked against the paper tables (remaining ones are model parameters or derived ratios).
- **Deviations / decisions:**
  1. Table selection by content (parameters, nominal, loop margins, anti-windup ablation, load, Pareto, noise, Sobol). The ticket's "Tables 1, 2, 3, 5, 6, 8" follows an older numbering in which Table 8 is now the NMPC table. Fouling sweep not included (not in the requested scope).
  2. Noise campaign: **1200** runs (8 tunings × 5 σ × 30 seeds), not 1500 — the 1500 of the base paper included the two NMPCs.
  3. **Anti-windup ablation is now scripted** (`antiwindup_ablation.tex`, `results/jpc/antiwindup_ablation.csv`). It reproduces ZN IAE = 104.123 and CC = 102.668 K·min with naive clamping. The `IC-T10` value for CC (107.12) does not reproduce and was not used. Nuance reported in the text: for low-gain SIMC the naive rule gives a *lower* IAE (1.089 vs 1.288), so directional clamping prevents loss of control of high-gain loops rather than being uniformly faster.
  4. Highlight changed from "thermal runaway" to "lose temperature control": with naive clamping the reactor is over-cooled and leaves the setpoint, it does not run away.
  5. Section file names follow the advisor prompt (`02_plant_actuator_limits.tex`), not the ticket (`02_modeling_actuator.tex`).
  6. The one remaining overfull box > 15 pt (123.6 pt) is produced by the cas-dc keywords front-matter box itself (reproduced in a minimal cas-dc document); it was reported, not suppressed with `\hfuzz`.

### 4. `IC-T15` — Artigo 2 (CACE)
- `02_Computers_Chemical_Engineering/main.pdf`: **11 pages**, 0 errors, 0 undefined refs/citations, no overfull box > 15 pt, **0 Ziegler-Nichols/Cohen-Coon mentions**. Highlights 72/70/71/77 characters. CSV mirrors in `results/cace/`.
- 61 of 63 table rows are identical to `results/*.csv`; the 2 differences are only the hardware-dependent NMPC step times, re-measured in this run (Oracle 31.46 vs 32.70 ms; MHE 39.28 vs 39.21 ms). All control metrics are identical.

### 5. `IC-T16` — Artigo 3 (ChERD)
- New campaign `experiments/exp_06_unstable_saddle_and_fouling.py` (CSV mirrors in `results/cherd/`), tests `tests/test_cascade_and_unstable.py` (11 passed). `03_Chemical_Engineering_Research_Design/main.pdf`: **11 pages**, 0 errors, 0 undefined refs, no overfull box > 15 pt. Highlights 78/80/79/78 characters.
- **Ticket premise is false and the operating point was changed (needs advisor approval):** at the nominal feed $T_f = 350$ K the plant has a single, stable steady state (396.65 K, max Re λ = −1.571) for every coolant flow, so no unstable saddle exists near 345 K. Artigo 3 uses a cooled feed $T_f = 320$ K with $q_j = 55.38$ L/min, which gives three equilibria (322.65, 345.00, 378.97 K); the middle one is a saddle with λ = +0.744 min⁻¹. Independently re-verified by the parent session. Consequence: Artigo 3 operates at a different point from Artigos 1 and 2; the text states it.

### 6. Open items for the orchestrator
- Artigo 3 contains **2 `[CITATION NEEDED]` markers** (fouling deposition rate proportional to reaction rate, `sections/04_fouling.tex`; master-gain ratio shortcut in sequential cascade tuning, `sections/03_control_design.tex`). No suitable key exists in `references.bib`; none was invented.
- Decide whether the $T_f = 320$ K operating point of Artigo 3 is acceptable or whether the paper should be reframed.
- Artigos 2 and 3 have no `ready-to-overleaf/` folder or ZIP (not requested by their tickets).
- Prose of Artigos 2 and 3 was checked for compilation, table integrity and the saddle physics, not read line by line by the parent session.
- The Data Availability statements point to `https://github.com/Marques-svnt/IC-CSTR-Control-Benchmark`; the repository content was not verified (the local folder is not a git repo).
- `generate_maximum_paper_figures.py` and `generate_fig4_springer.py` remain obsolete; do not run them.


---

## Wave 5 — Git Scaffolding, Repository Normalization & Zenodo Protocol (`IC-T17` $\to$ `IC-T20`)

> **Instructions for Claude PRO:**
> Execute Wave 5 to transform the IC directory into the canonical public monorepo (`Marques-svnt/IC-CSTR-Control-Benchmark`).
> Maintain the Single Source of Truth for simulations (`src/`), clean up obsolete legacy artifacts, normalize the papers directory, configure strict `.gitignore` rules, initialize git, create the initial semantic commit, and tag `v1.0.0-jpc-submission`.

---

### [x] `IC-T17`: Directory Normalization (`papers/`) & `.gitignore` Sanitization
- **Blocked by:** Wave 4
- **Files / Paths:**
  - `.gitignore`
  - `papers/01_journal_of_process_control/`
  - `papers/02_computers_chemical_engineering/`
  - `papers/03_chemical_engineering_research_design/`
  - `archive/legacy_drafts/`
- **Accomplishments:**
  - Migrated `Artigos_Rascunhos/` into canonical `papers/` structure with 3 target journals.
  - Configured `.gitignore` with strict rules, ignoring `.venv`, build temporaries, literature PDFs in `Biblioteca/`, and sensitive files (`*.olauth`). Whitelisted paper figures (`*.pdf`), tables (`*.tex`), and results (`*.csv`).

---

### [x] `IC-T18`: Git Initialization, Author Identity & Semantic Initial Commit
- **Blocked by:** `IC-T17`
- **Accomplishments:**
  - Local repository initialized on branch `main`.
  - Author identity configured: `Gabriel Marques de Andrade <marques.andrade@uesc.br>`.
  - Initial commit created with 6.95 MiB total size (< 15 MiB limit).

---

### [x] `IC-T19`: Entrypoint Modernization (`CLAUDE.md`, `pyproject.toml`, `README.md`)
- **Blocked by:** `IC-T18`
- **Accomplishments:**
  - Updated `CLAUDE.md` to reference `papers/` structure, 124 passed tests, and active ticket queue.
  - Documented reproduction recipes and build assets.

---

### [x] `IC-T20`: Semantic Release Tagging (`v1.0.0-jpc-submission`) & Test Suite Audit
- **Blocked by:** `IC-T19`
- **Accomplishments:**
  - Tag `v1.0.0-jpc-submission` created and pushed to GitHub.
  - Full pytest verification: 124 passed, 1 expected xfail (TL-PID).
  - All 3 manuscripts compile with 0 errors.
  - Pushed to `git@github.com:Marques-svnt/IC-CSTR-Control-Benchmark.git` with legacy branch preserved at `archive/legacy-monolith`.

---

## Execution Report — Wave 5 (`IC-T17` → `IC-T20`) (2026-10-22)
- **Status:** All four tickets completed, audited, hardened and pushed to GitHub.
- **Remote URL:** `git@github.com:Marques-svnt/IC-CSTR-Control-Benchmark.git`
- **Branch `main`:** Synchronized with commit `c9ac4b5`.
- **Branch `archive/legacy-monolith`:** Preserves old history (`1c840b5`).
- **Release Tag:** `v1.0.0-jpc-submission` points to `c9ac4b5`.
- **Security Audit:** Overleaf session credentials (`.olauth`) and pickle caches purged from Git.
- **LaTeX Footer Fix:** `cas-common.sty` uncommented `\clearpage` in `\AtEndDocument`, fixing the "Page 10 of 8" footer anomaly across all papers.



---

## Wave 6 — Peer-Review Remediation: Multi-Branch Concurrent Orchestration (`IC-T21` $\to$ `IC-T27`)

> **Architecture: Hub-and-Spoke (3 Branch Conversations $\to$ Main Coordinator)**
> Rather than a slow sequential queue, Wave 6 is organized into **three concurrent branch conversations** (one dedicated branch per paper) that work in parallel and report back to the **Main Coordinator Conversation**:
>
> 1. **Branch 1 (`fix/paper1-jpc-remediation`):** Executes `IC-T21` + `IC-T22` (*Journal of Process Control*). Compute: **Low** ($\approx 1-2\text{ min}$).
> 2. **Branch 2 (`fix/paper2-cce-remediation`):** Executes `IC-T23` + `IC-T24` (*Computers & Chemical Engineering*). Compute: **High** ($\approx 25-35\text{ min}$ due to CasADi/IPOPT NMPC in closed loop). Use Latin Hypercube Sampling ($N=25-30$) and `joblib` multi-core parallelization.
> 3. **Branch 3 (`fix/paper3-cerd-remediation`):** Executes `IC-T25` + `IC-T26` (*Chemical Engineering Research and Design — CERD*). Compute: **Low** ($\approx 1\text{ min}$).
> 4. **Main Coordinator (Hub / `main`):** Receives branch reports, merges changes, validates cross-cutting dependencies in `src/`, and executes `IC-T27` (cross-paper metadata, unified pytest suite, and Overleaf bundling).
>
> **Target Journals (Locked):**
> - **Paper 1:** *Journal of Process Control* (Elsevier, IFAC) — Qualis A1
> - **Paper 2:** *Computers & Chemical Engineering* (Elsevier) — Qualis A1
> - **Paper 3:** *Chemical Engineering Research and Design* (CERD, Elsevier / IChemE) — Qualis A1

---

### Computational Cost Profiling Summary:
- `IC-T21`: **Negligible** ($\approx 2-4\text{ s}$). 40 ODE runs (PID + CSTR RK4).
- `IC-T22`: **Low** ($\approx 1-2\text{ min}$). Exact linear algebra ($H_\infty$) + 840 short filtered ODE runs + Nelder-Mead.
- `IC-T23`: **Moderate** ($\approx 4-6\text{ min}$). 12 NMPC runs with CasADi/IPOPT ($500$ steps $\times$ $35\text{ ms}$).
- `IC-T24`: **HIGH COMPUTATIONAL DEMAND** ($\approx 25-35\text{ min}$ serial / $\approx 5-7\text{ min}$ parallel). Requires closed-loop NMPC evaluations across parametric mismatch and stochastic noise. **Mitigation:** Employ Latin Hypercube Sampling ($N=25-30$ points) and parallelize with `joblib.Parallel(n_jobs=-1)`.
- `IC-T25`: **Negligible** ($\approx 3-5\text{ s}$). ODE fouling sweeps and $3 \times 3$ eigenvalue tracking.
- `IC-T26`: **Low** ($\approx 30-45\text{ s}$). Scheduled cascade ODE and Nelder-Mead SISO optimization.
- `IC-T27`: **Negligible** ($\approx 30\text{ s}$). `pytest` suite + `latexmk -pdf` compilation.

---

### [x] `IC-T21`: [Paper 1 - JPC] Reframe Scope & Complete $2 \times 2$ Anti-Windup Ablation with Back-Calculation
- **Paper:** `papers/01_journal_of_process_control/`
- **Target Journal:** *Journal of Process Control* (Qualis A1)
- **Reviewer Consensus Issue:** Scope risk (JPC excludes PID tuning shootouts) + Ablation is a strawman (naive clamping never triggers for $K_p < 0$, valve gets stuck at 100% cooling = $377.9\text{ K}$, explaining identical $842.5\%$ IAE; missing tracking/back-calculation).
- **Files:**
  - `src/classical_control/pid_controller.py`
  - `experiments/build_paper_assets.py`
  - `experiments/exp_01_classical_benchmark.py`
  - `papers/01_journal_of_process_control/sections/01_intro.tex`
  - `papers/01_journal_of_process_control/sections/03_pid_classical.tex`
  - `papers/01_journal_of_process_control/sections/04_results.tex`
  - `papers/01_journal_of_process_control/highlights.tex`
  - `tests/test_classical_control.py`
- **Requirements:**
  1. **Ablation & Anti-Windup Architecture (`pid_controller.py`):**
     - Add `AntiWindupMethod.NONE` (integrator accumulates freely without any clamping or feedback).
     - Add `AntiWindupMethod.BACK_CALCULATION` implementing standard tracking:
       $$\dot{v}_I(t) = \frac{K_p}{T_i} e(t) + \frac{1}{T_t} [u_{\text{act}}(t) - u_{\text{raw}}(t)]$$
       with tracking time constant $T_t = \sqrt{T_i T_d}$ (or $T_t = T_i$ when $T_d = 0$).
     - Implement full $2 \times 2$ factorial test matrix in `run_antiwindup_ablation`:
       - Factor 1: Trigger condition (Position-only saturation vs Position + Slew-rate saturation).
       - Factor 2: Sign awareness (Directional sign-aware $(u_{\text{raw}} - u_{\text{act}})(K_p e_k) > 0$ vs Sign-agnostic / unconditional).
     - In `results/` and Table 3, report all 5 cases: `None`, `Back-Calculation`, `Pos-only Agnostic`, `Pos+Rate Agnostic`, `Directional (Proposed)`.
     - Mechanically document why naive clamping fails: for $K_p < 0$, the old condition never froze the integrator, leaving cooling stuck at $300\text{ L/min}$ and $T = 377.9\text{ K}$.
  2. **Editorial Repositioning (JPC Scope Defense):**
     - Rewrite title, abstract, and highlights (< 85 chars): Reposition the paper from a "PID tuning comparison" to an "Implementation and benchmarking methodology for constrained actuators (amplitude and slew rate) with directional anti-windup in exothermic reactors".
     - In Section 1 and Section 3, cite concrete literature (Åström & Rundqwist 1989; Galeani et al. 2009; Tarbouriech & Turner 2009; Visioli 2006) instead of general textbooks when discussing anti-windup under velocity limits.
- **Acceptance Criteria:**
  - `pytest tests/test_classical_control.py` passes with tests for `NONE`, `BACK_CALCULATION`, and the $2 \times 2$ matrix.
  - Table 3 in Paper 1 updated with complete ablation.
  - Highlights conform to JPC char limit (< 85 chars per bullet).
  - Clean compilation of `papers/01_journal_of_process_control/main.pdf`.

---

### [x] `IC-T22`: [Paper 1 - JPC] Plant-Exact Robustness ($\|CS\|_\infty$, HF Gain), Measurement Filter & Out-of-Sample Validation
- **Blocked by:** `IC-T21`
- **Paper:** `papers/01_journal_of_process_control/`
- **Reviewer Consensus Issue:** $M_s$ from FOPTD is an apparent-delay artifact (exact linear plant has $M_s = 1.57$ for ZN and $1.75$ for CC); noise sensitivity is driven by high-frequency gain $|K_p|(1+N)$; noise campaign chatters at kinematic limit ($800\text{ L/min}$) without filter; Optimal ITAE evaluated in-sample; disturbance hits saturation ceiling ($297.3 / 300\text{ L/min}$).
- **Files:**
  - `src/classical_control/foptd.py`
  - `src/classical_control/closed_loop.py`
  - `src/classical_control/tuning_optimization.py`
  - `experiments/exp_01_classical_benchmark.py`
  - `experiments/exp_02_robustness_campaign.py`
  - `papers/01_journal_of_process_control/sections/04_results.tex`
  - `papers/01_journal_of_process_control/sections/05_conclusion.tex`
  - `papers/01_journal_of_process_control/tables/`
- **Requirements:**
  1. **Exact Linearized Robustness Metrics:**
     - Compute $\|S\|_\infty$, $\|T\|_\infty$, and control sensitivity $\|CS\|_\infty$ using the exact 3-state linearized model $(A, B, C)$ with ZOH.
     - Compute explicit high-frequency gain $K_{\text{hf}} = |K_p|(1+N)$ (e.g. 490 L/min/K for ZN, 559 for CC, 77 for SIMC).
     - In Section 4.4, 4.7, and Conclusion 2, explain that noise vulnerability in ZN/CC stems from $K_{\text{hf}}$ and $\|CS\|_\infty$, not an unstable sensitivity peak in the physical plant.
  2. **Filtered Measurement Campaign & Paired Statistics:**
     - Add measurement low-pass filter on reactor temperature: $\dot{T}_{\text{meas}} = \frac{1}{\tau_f}(T_{\text{true}} + \eta - T_{\text{meas}})$ with $\tau_f = 0.05\text{ min}$ (or derivative filter $N = 10$).
     - Re-run noise campaign across $\sigma \in \{0.0, 0.01, 0.05, 0.10\}\text{ K}$. Verify that TV does not saturate at $800\text{ L/min}$ and discriminates valve wear.
     - Add 95% confidence intervals and paired Wilcoxon/t-tests across the 30 seeds in Table 7.
  3. **Out-of-Sample Setpoint Evaluation:**
     - Evaluate all controllers on setpoint steps not seen during ITAE optimization: $\Delta T_{\text{sp}} \in \{-5, -1, +1, +2, +5\}\text{ K}$.
     - Re-optimize 2-DOF Optimal ITAE with free $(\beta, \gamma) \in [0, 1]^2$ rather than fixing $\beta = 0.5$.
  4. **Graduated Disturbance Scenarios:**
     - Replace extreme $T_f + 5\text{ K}, C_{Af} + 20\%$ (which requires $297.3\text{ L/min}$ cooling, leaving only $2.7\text{ L/min}$ before saturation) with moderate disturbances ($T_f + 2\text{ K}$, $C_{Af} + 10\%$) that allow controllers to demonstrate regulatory performance without being crushed against the actuator ceiling.
- **Acceptance Criteria:**
  - `pytest tests/test_classical_control.py tests/test_metrics.py` passes.
  - Tables 4, 5, 6, 7 and Figure 2/5 updated in `papers/01_journal_of_process_control/`.
  - PDF compiles cleanly with 0 errors.

---

### [x] `IC-T23`: [Paper 2 - CCE] Offset-Free NMPC Formulation (Disturbance State/Integral Action) & Horizon Audit
- **Paper:** `papers/02_computers_chemical_engineering/`
- **Target Journal:** *Computers & Chemical Engineering* (Qualis A1)
- **Reviewer Consensus Issue:** NMPC has $+8.7\text{ K}$ to $+8.9\text{ K}$ offset under unmeasured feed disturbances, while PID has 0; comparing PID to an NMPC without disturbance model is comparing a complete controller to an incomplete one. Explanation of offset was inconsistent with model steady states.
- **Files:**
  - `src/controllers/optimal/nmpc_controller.py`
  - `experiments/exp_01b_nmpc_oracle_comparison.py`
  - `papers/02_computers_chemical_engineering/sections/03_nmpc_mhe.tex`
  - `papers/02_computers_chemical_engineering/sections/04_results.tex`
  - `tests/test_sobol_and_nmpc.py`
- **Requirements:**
  1. **Offset-Free NMPC Implementation (`nmpc_controller.py`):**
     - Augment the NMPC formulation with an integrating disturbance model or state-tracking error integral:
       - Either add disturbance state $d_k$ to the temperature balance: $\dot{T} = f_T(x, u) + d$, with $d$ estimated by the augmented MHE/EKF.
       - Or add an explicit integral penalty state $z_{k+1} = z_k + \Delta t (T_k - T_{\text{sp}})$ into the stage cost $J = \sum (T - T_{\text{sp}})^2 Q_T + q_j^2 R_u + \Delta q_j^2 R_{\Delta u} + z^2 Q_I$.
     - Re-run disturbance scenario ($T_f + 5\text{ K}$, $C_{Af} + 20\%$) and verify that steady-state offset drops from $+8.8\text{ K}$ to $< 0.05\text{ K}$.
  2. **Diagnostic Analysis of Original Offset:**
     - Perform horizon sweep $N \in \{30, 50, 75, 100\}$.
     - Plot predicted horizon trajectory vs realized closed-loop trajectory to prove whether short horizon ($N=50 \implies 1.0\text{ min}$, allowing only $\Delta q_j = 80\text{ L/min}$) causes perpetual postponement of control action.
     - Correct explanation in Section 4.6 (replace the claim that nominal equilibrium was already at $T_{\text{sp}}$ with actual steady-state energy balance values: $111\text{ L/min}$ nominal vs $166\text{ L/min}$ disturbed).
- **Acceptance Criteria:**
  - Unit test in `tests/test_sobol_and_nmpc.py` verifies offset-free tracking under unmeasured $T_f$ step ($|e_{\text{ss}}| < 0.05\text{ K}$).
  - Table 5 of Paper 2 regenerated with Offset-Free NMPC showing zero offset.
  - Paper 2 PDF compiles cleanly.

---

### [x] `IC-T24`: [Paper 2 - CCE] De-confounding Controller Comparison, Symmetric Noise Filtering, & Thermodynamic Infeasibility Fix
- **Blocked by:** `IC-T23`
- **Paper:** `papers/02_computers_chemical_engineering/`
- **Reviewer Consensus Issue:** 21% gain confounds 3 factors ($\alpha_{UA}$ estimation, rate planning, nonlinearity); AMIGO was circularly selected post-hoc; valve travel was compared asymmetrically (Oracle without noise vs PID with noise); $60\%\text{ UA}$ is thermodynamically impossible in steady state ($UA_{\text{crit}} = 63.8\%$) yet reported as controller failure.
- **Files:**
  - `src/controllers/optimal/nmpc_controller.py`
  - `src/classical_control/pid_controller.py`
  - `experiments/exp_01b_nmpc_oracle_comparison.py`
  - `experiments/exp_02_robustness_campaign.py`
  - `papers/02_computers_chemical_engineering/sections/04_results.tex`
  - `papers/02_computers_chemical_engineering/sections/05_conclusion.tex`
  - `papers/02_computers_chemical_engineering/tables/`
- **Requirements:**
  1. **Factor De-confounding Ablation:**
     - Run NMPC with frozen $\alpha_{UA} = 1.0$ during the 30% fouling transient.
     - Implement Gain-Scheduled PID: $K_p(\hat{\alpha}_{UA}) = K_{p0} / \hat{\alpha}_{UA}$ where $\hat{\alpha}_{UA}$ comes from the MHE/EKF.
     - Benchmark all standard PID rules (ZN, CC, TL, AMIGO, SIMC, Optimal ITAE) in the fouling transient rather than picking AMIGO post-hoc.
     - Isolate the percentage contribution of: (a) Online parameter adaptation; (b) Slew-rate constrained trajectory optimization; (c) Nonlinear phenomenological prediction.
  2. **Parametric Plant-Model Mismatch:**
     - Introduce $\pm 5\%$ to $\pm 10\%$ parametric mismatch in plant parameters ($E_a/R$, $k_0$, $\Delta H$, $T_f$, $C_{Af}$) between the true plant and the NMPC internal model.
     - Verify performance degradation via a 50-run Monte Carlo sweep.
  3. **Symmetric Noise & TV Reporting:**
     - Compare NMPC-MHE against PID with measurement filter.
     - Rephrase claims in abstract and text: report the true, fair valve travel reduction ($15-24\%$, not "less than half" or "four times less").
     - Clarify why NMPC-MHE had slightly lower IAE than Oracle in Tab. 7 (filter smoothing effect).
  4. **Thermodynamic Reality at $60\%\text{ UA}$:**
     - Prove mathematically that at $T = 394.65\text{ K}$, $UA_{\text{crit}} = 63.8\%$. At $UA = 60\%$, maximum cooling ($300\text{ L/min}$) yields an equilibrium of $396.65\text{ K} > T_{\text{sp}}$.
     - Remove $60\%\text{ UA}$ from the "controller shootout" ranking; present it in Section 4.5 as a demonstration of thermodynamic loss of controllability. Correct Conclusion 5.
- **Acceptance Criteria:**
  - De-confounding table generated in `papers/02_computers_chemical_engineering/tables/`.
  - Claims of valve travel reduction adjusted to 15–24% with symmetric noise.
  - $UA_{\text{crit}} = 63.8\%$ explicitly formulated and explained in text.
  - Paper 2 PDF compiles cleanly.

---

### [x] `IC-T25`: [Paper 3 - CERD] Dynamic Fouling Sweep ($\kappa_{\text{foul}}$), Stability Mechanism Correction, & Numerical $b_3$ Fix
- **Branch:** `fix/paper3-cerd-remediation`
- **Paper:** `papers/03_chemical_engineering_research_design/`
- **Target Journal:** *Chemical Engineering Research and Design* (CERD, Elsevier / IChemE, Qualis A1)
- **Compute Cost:** Negligible ($\approx 3-5\text{ s}$).
- **Reviewer Consensus Issue:** Mechanism of instability loss is dynamic (complex conjugate pair crossing imaginary axis), NOT loss of actuator gain ($K_c k \approx 1.5 > 1$ at boundary); headline 86–89% is frozen linear eigenvalue criterion, whereas dynamic simulation regulates until $52\%\text{ UA}$ ($t=28\text{ min}$); numerical discrepancy in $b_3$ ($-0.268$ vs $-0.315\text{ K/L}$).
- **Files:**
  - `src/sim_core/cstr_plant.py`
  - `experiments/exp_06_unstable_saddle_and_fouling.py`
  - `papers/03_chemical_engineering_research_design/sections/04_thermal_limits.tex`
  - `papers/03_chemical_engineering_research_design/sections/05_cascade.tex`
  - `papers/03_chemical_engineering_research_design/highlights.tex`
  - `tests/test_cstr_model.py`
- **Requirements:**
  1. **Correction of Instability Mechanism:**
     - Plot $K_c \cdot k$ along $UA \in [0.4, 1.0]$ and demonstrate that at $UA = 89.25\%$ (SISO) and $86.15\%$ (cascade), $K_c \cdot k = 1.57$ and $1.49$ (well above the static threshold of 1.0).
     - Plot the root locus / eigenvalue trajectories $\lambda(UA)$: prove that instability occurs via a complex conjugate pair crossing the imaginary axis ($\mathrm{Re}(\lambda) = 0, \mathrm{Im}(\lambda) \neq 0$), representing an oscillatory dynamic bifurcation, not static gain collapse.
     - Rewrite Section 4.3, 5.2, and Figure 5 to eliminate "loss of actuator gain" and correctly explain the dynamic eigenvalue crossing.
  2. **Dynamic Fouling Rate Sweep ($\kappa_{\text{foul}}$):**
     - Run dynamic simulations across fouling rates $\kappa_{\text{foul}} \in \{0.005, 0.05, 0.5\}\text{ min}^{-1}$.
     - Demonstrate that as $\kappa_{\text{foul}} \to 0$ (quasi-static fouling), the dynamic departure time converges asymptotically to the frozen eigenvalue boundary ($86-89\%$).
     - Rephrase abstract, Highlight 4, and Conclusion 5 to explicitly distinguish between the "analytical linear stability boundary ($86-89\%$)" and the "practical loss of regulation in fast transients ($52\%$ for SISO)".
  3. **Numerical Discrepancy Resolution in $b_3$:**
     - Recalculate $b_3 = \frac{\partial \dot{T}_j}{\partial q_j} = \frac{T_{jf} - \bar{T}_j}{V_j}$ at $UA_{\text{crit}}$.
     - Verify with $\bar{T}_j = \bar{T} - Q_{\text{load}}/UA_{\text{crit}} = 305.35\text{ K}$: $b_3 = -0.268\text{ K/L}$ (factor 5.4) vs $-0.315\text{ K/L}$ (factor 4.6). Fix the number and factor in Section 4.3.
- **Acceptance Criteria:**
  - `pytest tests/test_cstr_model.py` passes.
  - Figure 5 updated with eigenvalue root locus and $K_c \cdot k(UA)$.
  - Abstract and highlights updated with dual linear/dynamic distinction.
  - Paper 3 PDF compiles cleanly.

---

### [x] `IC-T26`: [Paper 3 - CERD] Slave Gain-Scheduling Simulation, Robustness Bounds ($\|S\|_\infty \ge e^{p\theta}$), & Optimized SISO Baseline
- **Blocked by:** `IC-T25`
- **Branch:** `fix/paper3-cerd-remediation`
- **Paper:** `papers/03_chemical_engineering_research_design/`
- **Target Journal:** *Chemical Engineering Research and Design* (CERD, Elsevier / IChemE, Qualis A1)
- **Compute Cost:** Low ($\approx 30-45\text{ s}$).
- **Reviewer Consensus Issue:** Core practical recommendation (gain scheduling slave loop) was never simulated; SISO baseline was unoptimized SIMC with slow dominant pole; fundamental robustness lower bound $\|S\|_\infty \ge 1.62$ was not reported; lack of parametric sensitivity.
- **Files:**
  - `src/classical_control/cascade_controller.py`
  - `src/classical_control/tuning_optimization.py`
  - `experiments/exp_05_cascade_benchmark.py`
  - `experiments/exp_06_unstable_saddle_and_fouling.py`
  - `papers/03_chemical_engineering_research_design/sections/03_open_loop_saddle.tex`
  - `papers/03_chemical_engineering_research_design/sections/05_cascade.tex`
  - `papers/03_chemical_engineering_research_design/sections/06_conclusions.tex`
  - `papers/03_chemical_engineering_research_design/tables/`
- **Requirements:**
  1. **Simulate Slave Gain-Scheduling:**
     - Implement scheduled slave controller in `src/classical_control/cascade_controller.py`:
       $$K_{c2}(T_j) = K_{c2,0} \frac{\bar{T}_{j,0} - T_{jf}}{T_j - T_{jf}}$$
     - Re-run fouling campaign with scheduled cascade; report in Table 6 and Figure 5 that stability is extended well beyond $86.15\%$.
  2. **Optimized SISO PID Baseline:**
     - Replace the unoptimized SIMC SISO baseline ($\tau_c = 0.10$, dominant pole at $-0.064\text{ min}^{-1}$) with an optimal PID baseline tuned with explicit constraint $M_s \le 1.60$.
     - Evaluate disturbance rejection in a fixed time window ($t \in [0, 15]\text{ min}$) to prevent limit-cycle horizon inflation.
     - Recalculate the true fair IAE reduction of cascade vs optimal SISO.
  3. **Fundamental Robustness Bounds & Sensitivities:**
     - For unstable saddle pole $p = 0.7435\text{ min}^{-1}$ and delay $\theta = 0.648\text{ min}$, report the fundamental bound $\|S\|_\infty \ge e^{p\theta} \approx 1.62$.
     - Report $M_s$, gain margin, phase margin, and delay margin for both SISO and cascade loops.
     - Run a Monte Carlo sensitivity sweep on $E_a/R$, $k_0$, and $\Delta H$ ($\pm 5\%$) to quantify robustness under saddle hypersensitivity.
- **Acceptance Criteria:**
  - Scheduled cascade implemented and tested in `tests/test_classical_control.py`.
  - Table 6 updated with scheduled cascade and optimized SISO baseline.
  - Robustness margins and sensitivity bound documented in Section 3 and 5.
  - Paper 3 PDF compiles cleanly.

---

### [x] `IC-T27`: [Cross-Paper] Editorial Hygiene, Authorship Norms (CRediT, ORCID, AI Disclosure) & Zenodo Bundling
- **Blocked by:** `IC-T21`, `IC-T22`, `IC-T23`, `IC-T24`, `IC-T25`, `IC-T26`
- **Papers:** All three manuscripts (`papers/01_...`, `papers/02_...`, `papers/03_...`)
- **Reviewer Consensus Issue:** Missing CRediT statements in Papers 1 & 2; empty ORCID; missing Generative AI disclosure statements; unresolved "companion papers under review" self-citations; missing definitions of $M_p$, $t_s$, units in ITAE ($\text{K}\cdot\text{min}^2$).
- **Files:**
  - `papers/01_journal_of_process_control/main.tex`
  - `papers/02_computers_chemical_engineering/main.tex`
  - `papers/03_chemical_engineering_research_design/main.tex`
  - `papers/01_journal_of_process_control/references.bib`
  - `papers/02_computers_chemical_engineering/references.bib`
  - `papers/03_chemical_engineering_research_design/references.bib`
  - `Makefile`
- **Requirements:**
  1. **CRediT & Metadata Uniformity:**
     - Add formal Elsevier CRediT authorship statement to Paper 1 and Paper 2 matching Paper 3:
       `Gabriel Marques de Andrade: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data Curation, Writing - Original Draft, Writing - Review & Editing, Visualization.`
     - Populate author ORCID: `0009-0008-8868-5100`.
     - Add explicit Elsevier-compliant Generative AI disclosure statement in backmatter of all three papers.
  2. **Nomenclature & Units Sanitation:**
     - Explicitly define $M_p$ (% overshoot) and $t_s$ (2% settling band criterion) in all nomenclature sections and table footnotes.
     - Ensure all occurrences of ITAE carry explicit units ($\text{K}\cdot\text{min}^2$).
     - Merge redundant tables (e.g. Table 2 and Table 6 in Paper 1).
  3. **Bibliography Modernization & Overleaf Archives:**
     - Add recent literature (2019–2026) on rate-limited anti-windup, CSTR control benchmarks, and NMPC/MHE.
     - Cleanly resolve citations between the 3 companion papers (cite as companion preprints with title and GitHub/Zenodo repository).
     - Run `make papers` or compilation script; verify all three `main.pdf` compile with 0 LaTeX errors, 0 undefined citations, and 0 overfull boxes $> 15\text{ pt}$.
     - Rebuild `ready_to_overleaf.zip` for each paper and generate SHA-256 checksums.
- **Acceptance Criteria:**
  - All 3 manuscripts compile cleanly with 0 errors.
  - CRediT, ORCID, and AI statements present in all 3 papers.
  - `ready_to_overleaf.zip` updated for all three papers.
  - Test suite passes: `.venv/bin/pytest tests/`.


---

## Wave 8 — Paper 1 (JPC) literature audit, anti-mocking (`IC-T38`)

> Ticket: `Claude outputs/TICKET_PAPER1_LITAUDIT_ANTIMOCKING.md` · Branch: `jpc-v9-t38-litaudit` (from `jpc-v9`, not merged) · Report: `.antigravity/T38_REPORT.md`

### [x] `IC-T38`: [Paper 1 - JPC] Remove hand-typed literature-audit counts; make the "Loop action stated" row consistent
- **Paper:** `papers/01_journal_of_process_control/` (Paper 2 and 3 untouched)
- **Files:**
  - `papers/01_journal_of_process_control/repository/audit_coding.csv` (new `uses_pid` column), `repository/literature_audit.csv`
  - `scripts/jpc_numbers.py` (macro `litpid`, cross-checks, caption without fixed counts)
  - `experiments/build_paper_assets.py` (stiction caption uses `\ref{tab:stiction}`)
  - `papers/01_journal_of_process_control/{generated/numbers.tex,tables/literature_audit.tex,tables/antiwindup_deadband.tex}`, `results/jpc/v9_numbers.csv`
  - `papers/01_journal_of_process_control/{main.tex,supplementary.tex,sections/*.tex}` (advisor-revised text promoted from `overleaf-pós-revisões/`), `ready-to-overleaf/`, `ready_to_overleaf.zip`
- **Outcome:** author decision on article 2.1 (10.51485/ajss.v9i3.226): MPC with PSO-tuned parameters, no PID (predictive, `uses_pid = no`, anti-windup and loop action not applicable). Loop action row: 0 / 3 / 9 / 0; `vlitantiwindupapp` = 6, `vlitloopsignapp` = 3, `vlitpid` = 3.
- **Acceptance:** `jpc_numbers.py`, `check_text_numbers.py`, `check_main_supp_consistency.py`, `ruff`, `pytest` green; `main.pdf` and `supplementary.pdf` compile from the parent folder and from a clean extraction of `ready_to_overleaf.zip`.
- **Open for the author:** supplementary line "five items coded" vs seven rows in Table S36; second coder column empty.
