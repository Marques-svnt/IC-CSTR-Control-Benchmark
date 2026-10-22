# Engineering Specification — IC (`cstr-control-research`)
## Target: Qualis A1 / Q1 Approval (*Journal of Process Control* / *I&ECR* / *ChERD* / *CACE*)

### 1. Context & Wave 2 Peer-Review Audit Verdict
Tickets `IC-T01` through `IC-T05` were executed, raising the manuscript score to **70.6/100**.
To cross the **>92/100 Qualis A1 acceptance threshold**, the following **7 Major Technical Issues** and **4 Editorial/Typographical Red Flags** identified in the specialist peer review must be resolved in code, tables, figures, and LaTeX prose (`IC-T06` $\to$ `IC-T09`):

---

### 2. Root-Cause Analysis & Exact Mathematical Fixes (Wave 2)

#### 2.1 Issue 3.1 — Measurement Noise Leak into `NMPC-Oracle` (`src/controllers/optimal/nmpc_controller.py:499-505`)
- **Bug:** In `CstrNmpcController.compute()`, `self.estimator.step(..., t_meas=float(measurement), ...)` is called unconditionally even when `self.feedback_mode == "oracle"`. Because `measurement = T_true + noise`, the noisy thermocouple reading perturbs `self._estimated_alpha_ua = float(x_est[3])` via `mhe_residual`, which then enters `tvp_fun` (`tvp_template["_tvp", :, "alpha_ua"] = self._estimated_alpha_ua`), causing `NMPC-Oracle` `TV` to jump from $152.5\text{ L/min}$ ($\sigma=0$) to $557.4\text{ L/min}$ ($\sigma=1.0\text{ K}$) in Table 6!
- **Fix:**
  1. In `CstrNmpcController`, add `true_alpha_ua: Optional[float] = None` (defaulting to `1.0`, or updated from `plant.params.UA` / disturbance when in `"oracle"` mode).
  2. When `self.feedback_mode == "oracle"` and `full_state is not None`, NEVER pass the noisy `measurement` to `self.estimator.step()`. Feed `t_meas=float(full_state[1])` and `t_j_meas=float(full_state[2])` (or use `self.true_alpha_ua` directly), ensuring that `NMPC-Oracle` is **100% invariant to sensor noise $\sigma$** (`IAE` and `TV` have $\pm 0.00$ std across all $\sigma \in \{0.0, 0.1, 0.2, 0.5, 1.0\}\text{ K}$ in Table 6 and Figure 6).

#### 2.2 Issue 3.2 — Computing `IAE` on True Reactor Temperature $T_{\text{true}}(t)$ (`src/classical_control/closed_loop.py:156-162`)
- **Bug:** `ClosedLoopSimulator.run()` passes `y=t_pv_arr` (the noisy sensor signal $T(t) + \eta(t)$) to `evaluate_performance()`, creating an artificial noise floor of $\mathbb{E}[|\eta|] t_f \approx 8.0\text{ K}\cdot\text{min}$ at $\sigma = 1.0\text{ K}$ in Table 6.
- **Fix:** Pass `y=states[:, 1]` (the true physical reactor temperature $T_{\text{true}}(t)$) to `evaluate_performance()` in `closed_loop.py:158` so $\mathrm{IAE} = \int |T_{\text{sp}}(t) - T_{\text{true}}(t)|\,dt$ measures actual physical thermal deviation induced by noise propagation through the valve.

#### 2.3 Issue 3.3 — Exact Numerical Consistency Across Table 2, Table 4 ($100\%\text{ UA}$), and Table 6 ($\sigma = 0.0\text{ K}$) + Fouling Equilibrium
- **Bug:**
  1. `exp_01_classical_benchmark.py` (Table 2) applies the $-2\text{ K}$ step at $t_{\text{step}} = 0.0\text{ min}$ over $t \in [0, 10]\text{ min}$, whereas `exp_02_robustness_campaign.py` (Tables 4 and 6) applies the step at $t_{\text{step}} = 0.5\text{ min}$ over $t \in [0, 10]\text{ min}$ without shifting the ITAE time weight $(t - t_{\text{step}})$. Consequently, Table 2, Table 4 ($100\%\text{ UA}$), and Table 6 ($\sigma = 0$) report different IAE, ITAE, and TV values while the text on page 18 falsely claims they are identical.
  2. In `evaluate_performance()` (`src/evaluation/metrics.py`), add `t_step: float = 0.0` so $\mathrm{ITAE} = \int_{t_{\text{step}}}^{t_f} \max(0, t - t_{\text{step}})|e(t)|\,dt$.
  3. Unify the servo step protocol across Table 2, Table 4, and Table 6: apply the $-2\text{ K}$ step at $t_{\text{step}} = 0.0\text{ min}$ over $t \in [0.0, 10.0]\text{ min}$ (or if $t_{\text{step}} = 0.5\text{ min}$ is used for visualization pre-roll, use it identically in all three tables with $t \in [0.0, 10.5]\text{ min}$ and `t_step=0.5`) so that **every single number in Table 2, Table 4 ($100\%\text{ UA}$), and Table 6 ($\sigma=0.0\text{ K}$) matches to the last decimal place**.
  4. For the Fouling campaign (Section 4.3, $UA \in \{100\%, 90\%, 80\%, 70\%, 60\%\}$), clarify explicitly in `04_results.tex` (and/or initialize at the corresponding steady state where physically feasible) how the simultaneous $UA$ degradation at $t=0$ interacts with the $-2\text{ K}$ servo command.

#### 2.4 Issue 3.4 — Velocity (Slew-Rate) & Sign-Correct Anti-Windup (`src/classical_control/pid_controller.py:235-241` & Eq. 21)
- **Bug:**
  1. In `pid_controller.py:237-240`, `if self._last_u_unconstrained >= self.limits.u_max and error > 0.0:` forgot that $K_p < 0$ (`i_gain = kp / ti < 0`), so `error < 0` is what drives `u_unconstrained` positive toward `u_max`!
  2. Both `pid_controller.py` and Equation (21) (`03_pid_classical.tex:24-29`) only check amplitude limits ($u_{\max}, u_{\min}$) and fail to clamp the integrator during slew-rate saturation ($|u_{\text{raw},k} - u_{\text{act},k-1}| > S_{\max}\Delta t$).
- **Fix:**
  In `pid_controller.py` (when `self.anti_windup == AntiWindupMethod.CLAMPING`) and in Equation (21) of `03_pid_classical.tex`, clamp the integrator whenever the actuator is saturated in **either amplitude or slew-rate** and the integral increment $K_p e_k$ acts in the direction of saturation:
  $$\text{Freeze integration if } \big(u_{\text{raw},k-1} > u_{\text{act},k-1} \text{ and } K_p e_k > 0\big) \;\text{ or }\; \big(u_{\text{raw},k-1} < u_{\text{act},k-1} \text{ and } K_p e_k < 0\big)$$
  Equivalently: `if (self._last_u_unconstrained - self._last_u_applied) * (i_gain * error) > 0.0: should_integrate = False`.

#### 2.5 Issue 3.5 — 2-DOF AMIGO Symmetry & PI Nature of Optimal ITAE
- **Fix:**
  1. Add **2-DOF AMIGO** (`beta = 0.5, gamma = 0.0`, or Åström-Hägglund's prescribed $\beta$ for $r = 0.1455$) to `setup_controllers()` in `exp_02_robustness_campaign.py` (or report both `AMIGO (1-DOF)` and `2-DOF AMIGO` in Table 2 and Section 3.4/3.5), demonstrating fairly that AMIGO's high disturbance-rejection gain is designed by Åström & Hägglund to operate with 2-DOF setpoint weighting in servo tracking.
  2. Explicitly discuss in Section 3.4 and Section 4.1 why constrained Nelder-Mead (`Optimal ITAE`) converges to $T_d = 0.000\text{ min}$ (effectively a pure PI controller with $M_s = 1.22 < 1.60$): on a lag-dominant loop ($r = 0.1455$) with a hard valve slew-rate ceiling ($S_{\max} = 80\text{ L/min}^2$), derivative action amplifies initial rate saturation without accelerating post-ramp recovery.

#### 2.6 Issue 3.6 — Zero-Noise Consistency of `NMPC-Oracle` vs. `NMPC-MHE` & Rigorous MHE Formulation
- **Bug:** At $\sigma = 0$ and nominal $100\%\text{ UA}$ (Table 2), `NMPC-Oracle` had $TV = 144.0\text{ L/min}$ while `NMPC-MHE` had $TV = 84.4\text{ L/min}$ because:
  1. `AugmentedCstrStateEstimator.step()` propagated states with 1-step RK2 (`_f_augmented`) and Forward Euler inside `mhe_residual`, while assuming a constant $C_A$ across all 8 samples of the moving window (`ca_curr = theta[0]`), creating artificial model-mismatch innovation even at $\sigma = 0$!
- **Fix:**
  1. In `AugmentedCstrStateEstimator.step()`, propagate states using the same 4-substep **RK4** integrator used by `_build_model()` and the plant.
  2. In `mhe_residual(theta)`, forward-propagate the 3-state trajectory $[C_A, T, T_j]$ across the window $i = 0, \dots, L-1$ starting from `[ca_0, t_0, tj_0]` with parameter `alpha_curr` via RK4 (rather than holding `ca_curr` static across the window!). Thus, at $\sigma = 0$ and $\alpha_{UA} = 1.0$, the innovation `y_vec - H @ x_pred` and window residual are identically zero ($< 10^{-10}$), so `NMPC-MHE` and `NMPC-Oracle` produce **the exact same nominal trajectory and TV** at $\sigma = 0$!
  3. In Section 3.6 (`03_pid_classical.tex`), write out the explicit mathematical equations of the 4-state Augmented EKF + Moving Horizon refinement ($\mathbf{x}_a = [C_A, T, T_j, \alpha_{UA}]^\top$, $\dot{\alpha}_{UA} = 0$, $Q_e = \mathrm{diag}(10^{-4}, 10^{-2}, 10^{-2}, 5\times 10^{-4})$, $R_e = \mathrm{diag}(0.05, 0.05)$, $P_0 = \mathrm{diag}(0.05, 1.0, 1.0, 0.05)$).

#### 2.7 Issue 3.7 — Sequential Skogestad SIMC Tuning for the Cascade Architecture (`exp_05_cascade_benchmark.py` & Section 3.9)
- **Fix:** Replace the ad-hoc cascade gains ($K_{p1}=2.20, K_{p2}=-6.00$) with **Sequential Skogestad SIMC**:
  1. **Inner (Slave) Jacket Loop ($q_j \to T_j$):** From the linearized jacket balance $\dot{T}_j = 5.0 T - 10.0 T_j - 2.416 q_j$, $\tau_2 = 0.10\text{ min}, K_2 = -0.2416\text{ K/(L/min)}, \theta_2 = \Delta t = 0.02\text{ min}$. Selecting $\tau_{c2} = 0.10\text{ min}$ yields SIMC PI gains:
     $$K_{p2} = \frac{1}{K_2}\frac{\tau_2}{\tau_{c2} + \theta_2} = -3.45\text{ (L/min)/K}, \qquad T_{i2} = \min(\tau_2, 4(\tau_{c2}+\theta_2)) = 0.10\text{ min}$$
  2. **Outer (Master) Reactor Loop ($T_{j,\text{sp}} \to T$):** With the inner loop closed ($\theta_1 \approx \tau_{c2} + \theta_2 = 0.12\text{ min}, \tau_1 = 0.6427\text{ min}, K_1 = K/K_2 = +0.7666\text{ K/K}$) and selecting the same outer bandwidth $\tau_{c1} = 0.40\text{ min}$ as SISO SIMC:
     $$K_{p1} = \frac{1}{K_1}\frac{\tau_1}{\tau_{c1} + \theta_1} = +1.61\text{ K/K}, \qquad T_{i1} = 0.643\text{ min}, \qquad T_{d1} = 0.33\theta_1 = 0.040\text{ min}$$
  Update `exp_05_cascade_benchmark.py` and Section 3.9 (`03_pid_classical.tex`), eliminating the oscillatory response in Figure 9.

#### 2.8 Section 4 Editorial & Formatting Fixes (`02_modeling.tex`, `03_pid_classical.tex`, `04_results.tex`)
1. `02_modeling.tex:94`: Replace raw Markdown `**locally asymptotically stable in open loop**` with `\textbf{locally asymptotically stable in open loop}`.
2. `02_modeling.tex:78`: Place the steady-state jacket temperature $T_j(q_j, T) = \frac{q_j T_{jf} + (UA/\rho_j C_{pj}) T}{q_j + UA/\rho_j C_{pj}}$ in its own numbered display equation environment so it does not collide with equation numbers.
3. `02_modeling.tex:99-103`: Fix the `bmatrix` formatting of $\mathbf{A}$ in Equation (14) (`\setlength{\arraycolsep}{6pt}`) so `-19.923` and `-0.0528` have clear horizontal separation.
4. `03_pid_classical.tex:108`: Clean spacing between $e_p$, $e_i$, and $e_d$ in Equation (32).
5. `04_results.tex` / Table 10: Fix column header spacing (`\tabcolsep`) so `Total TV (L/min)` and `Max Valve (L/min)` never collide.


---

### 3. Wave 3 Specifications: Priorities P1–P7 Methodological Hardening (`>95/100`)

#### 3.1 P1: Display Equation for $T_{j,\min}(T)$ (`02_modeling.tex`)
- Promote the inline equation into a clean display environment:
  $$T_{j,\min}(T) = \frac{u_{\max} T_{jf} + (UA/\rho_j C_{pj})\,T}{u_{\max} + UA/\rho_j C_{pj}} > T_{jf}$$
  eliminating nested fractions in text mode and ensuring unambiguous PDF text-layer extraction.

#### 3.2 P2: Structural Origin of Apparent Dead Time & Relative Degree 2 Damping (`03_pid_classical.tex`, `04_results.tex`, `05_conclusion.tex`)
- From $\mathbf{A}, \mathbf{B}, \mathbf{C}$ in Eq. (14), the exact linearized transfer function is:
  $$G_{\text{true}}(s) = \frac{-2.416(s + 19.923)}{(s + 1.5712)(s + 11.8006)(s + 13.2693)}$$
- It possesses a minimum-phase LHP zero at $z_1 = -19.923\text{ min}^{-1}$ and relative degree 2.
- Its asymptotic phase approaches $-180^\circ$ from above (and $-90^\circ$ with derivative lead $T_d > 0$), preventing finite-frequency phase crossover in the delay-free ODE.
- The FOPTD surrogate introduces $e^{-\theta s}$ ($\theta = 0.0935\text{ min}$), which drops phase without bound, yielding high sensitivity peaks ($M_s = 4.14$ for ZN, $M_s = 4.54$ for CC).
- Actuator slew-rate limiting ($80\text{ L/min}^2$) and directional clamping convert large initial proportional kicks into a bounded ramp without windup.

#### 3.3 P3: Exact Closed-Inner-Loop Sub-Block $\mathbf{A}_{12}$ vs. Open-Loop Ratio Approximation (`03_pid_classical.tex`)
- Tightly regulating $T_j \to T_{j,sp}$ severs the thermal feedback $A_{32} = +5.0\text{ min}^{-1}$.
- The exact outer dynamics from $T_{j,sp}$ to $T$ follow the upper $2\times 2$ sub-block:
  $$\det(s\mathbf{I} - \mathbf{A}_{12}) = s^2 + 16.641s + 34.432 = (s + 2.426)(s + 14.215)$$
  yielding exact dominant time constant $\tau_{1,\text{exact}} = 0.412\text{ min}$ and static gain $K_{1,\text{exact}} = 0.579\text{ K/K}$.
- The open-loop ratio approximation ($K_1 = 0.766, \tau_1 = 0.643$) overestimates gain by $32\%$, intentionally prescribing a conservative master gain $K_{p1} = 1.61$ that provides robustness against slave-loop saturation.

#### 3.4 P4: Temporal Indexing in EKF+MHE Arrival Cost & Forward Chaining (`03_pid_classical.tex`)
- Arrival cost priors are explicitly evaluated at the window start $k - N_m + 1$:
  $$\min_{C_{A,0}, \alpha_{UA}} 4 \left\| \begin{bmatrix} C_{A,0} - \hat{C}_{A,k-N_m+1}^{\text{prior}} \\ \alpha_{UA} - \hat{\alpha}_{UA,k-N_m+1}^{\text{prior}} \end{bmatrix} \right\|^2 + \sum_{i=1}^{N_m - 1} \left[ (T_i - \tilde{T}_i)^2 + \frac{1}{4}(T_{j,i} - \tilde{T}_{j,i})^2 \right]$$
- Once $(C_{A,0}^*, \alpha_{UA}^*)$ is obtained, the state vector is forward-chained through $\mathbf{F}$ across $N_m - 1$ steps with applied inputs $u_{k-N_m+1:k-1}$ to compute terminal estimate $\hat{\mathbf{x}}_{a,k}$.

#### 3.5 P5: 1-DOF Optimal ITAE in Table 7 & Quantitative Anti-Windup Ablation
- Evaluated 1-DOF `Optimal ITAE` alongside 2-DOF Optimal ITAE in Table 7:
  - `AMIGO`: $\mathrm{IAE} = 6.927\text{ K}\cdot\text{min}$ ($+26.5\%$ vs Oracle).
  - `Optimal ITAE ($M_s \le 1.6$)` (1-DOF): $\mathrm{IAE} = 7.312\text{ K}\cdot\text{min}$ ($+33.6\%$ vs Oracle, $M_p = 3.3\%$).
  - `2-DOF Optimal ITAE`: $\mathrm{IAE} = 7.707\text{ K}\cdot\text{min}$ ($+40.8\%$ vs Oracle, $M_p = 0.0\%$).
  - `NMPC-Oracle`: $\mathrm{IAE} = 5.474\text{ K}\cdot\text{min}$ ($+0.0\%$, reduces best PID IAE by $21.0\%$, 1-DOF Optimal ITAE by $25.1\%$).
- Documented quantitative failure under naive sign-blind amplitude-only clamping: $\mathrm{IAE} > 104\text{ K}\cdot\text{min}$, $M_p > 845\%$.

#### 3.6 P6: Trapezoidal Clamping Consistency (`src/classical_control/pid_controller.py`)
- Clamping check and integration step both use $e_{\text{trap}} = 0.5(e_k + e_{k-1})$:
  $$\text{Freeze if } (u_{\text{raw},k-1} - u_{\text{act},k-1})\left(\frac{K_p}{T_i} \frac{e_k + e_{k-1}}{2}\right) > 0$$
- Eliminates implicit algebraic loop between $I_k$ and $u_{\text{act},k}$.

#### 3.7 P7: Typography & Figure 5(a)
- Fixed `(*stiction*)` $\to$ `(\emph{stiction})`.
- Fixed units in Table 1: $\text{cal}/(\text{L}\cdot\text{K})$ and $\text{cal}/(\text{min}\cdot\text{K})$.
- Verified zero label collisions in `fig4_pareto_iae_tv.png`.

---

### 4. Wave 4 Specifications: Elsevier Modularization & Journal Splitting

#### 4.1 Target Journals & Architectural Isolation
Following the advisor's directive, the 37-page CSTR monograph is split into three independent Qualis A1 publications in the Elsevier two-column `cas-dc.cls` environment:

1. **Artigo 1 (`Journal of Process Control`):**
   - Title: *Robust PID Tuning under Actuator Saturation in Nonlinear Exothermic CSTRs: Performance, Anti-Windup and Sensitivity Trade-offs*
   - Scope: Purely linear robust feedback (ZN, CC, TL, AMIGO, 2-DOF AMIGO, SIMC, Optimal ITAE $M_s \le 1.6$, 2-DOF Optimal ITAE).
   - Core Assets: Directional clamping under slew-rate ($80\text{ L/min}^2$), Pareto continuous locus, 1500 Monte Carlo noise realizations, Sobol global sensitivity.
   - Negative Constraint: **Zero NMPC mentions or tables.**

2. **Artigo 2 (`Computers & Chemical Engineering`):**
   - Title: *When Does Nonlinear Model Predictive Control Outperform Robust PID? A Comparative Study under Fouling and Actuator Constraints*
   - Scope: Non-linear control payoff bounds.
   - Core Assets: NMPC-Oracle vs. NMPC-MHE (Augmented state $[C_A, T, T_j, \alpha_{\text{UA}}]$) vs. AMIGO and 1-DOF Optimal ITAE. Nominal step (+2.3% gain) vs. abrupt fouling (+21.0% to 25.2% gain), unmeasured disturbance offset limitation, CPU latency (32.7 ms vs 39.2 ms vs 0.09 ms).
   - Negative Constraint: **Zero empirical rule strawmen (ZN/CC).**

3. **Artigo 3 (`Chemical Engineering Research and Design`):**
   - Title: *Thermal Controllability Limits and Cascade Control in Exothermic CSTRs under Cooling Capacity Degradation*
   - Scope: Physical controllability boundaries and multi-loop thermal regulation without physical bench.
   - Core Assets: Operation inside the metastable unstable saddle window ($T = 345\text{ K}$, $\lambda_1 > 0$), continuous dynamic fouling kinetics $\frac{d(UA)}{dt} = -\kappa_{\text{foul}} r_A(C_A, T)$, time-to-runaway $t_{\text{runaway}}$, and feedforward utility compensation ($T_{jf}$).
