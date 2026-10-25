# Cover letter — Journal of Process Control

**Manuscript:** Anti-Windup under Amplitude and Slew-Rate Limits in Reverse-Acting Process Loops: An Implementation Study on an Exothermic CSTR

**Authors:** Gabriel Marques de Andrade (corresponding), Elilton Rodrigues Edwards — State University of Santa Cruz (UESC), Brazil

Dear Editor,

We submit the manuscript above as a regular paper. Its subject is **constraint handling in the discrete implementation of PID loops**: the difference equations of the integrator, the order in which amplitude, slew-rate and backlash limits are evaluated, the discretization of the tracking and measurement-filter terms, and the signals fed back to the anti-windup logic. We show, on the reverse-acting temperature loop of an exothermic CSTR and on a second plant, that these choices can decide which controller wins a simulation benchmark. We keep apart two groups: choices of the controller implementation, and the specification of the actuator model (backlash, deadband, stiction), which belongs to the plant but also changes the verdict. The paper is neither a PID tuning study nor a proposal of a new anti-windup rule. The six PID loops are a fixed-gain test bed, and the rule we adopt is the known sign-of-increment form of conditional integration.

**What the paper shows.**
1. **Sign-blind clamping.** Clamping written for a direct-acting loop and reused in a reverse-acting one latches the valve at full cooling. A proposition gives sufficient conditions, which the reactor reaches by simulation.
2. **The slew-rate trigger, not sign awareness.** A seven-policy ablation, including a 2×2 factorial, attributes the recovery to the slew-rate trigger. It covers three steps, a load profile, deadband, stiction and three operating points; a measured valve position fed back to the anti-windup is tested separately.
3. **Back-calculation matches the directional rule only without noise.** With one tracking constant per loop, selected on the design step and judged on ±5 K steps, back-calculation matches the directional rule without measurement noise, but not with it. We identify the mechanism: the tracking term integrates noise-induced cuts.
4. **Discretization and order matter selectively.** Explicit Euler instead of exact discretization of the measurement filter (a controller choice) and a backlash placed before the slew limit (a property of the actuator model) change the IAE by up to 24.2% and 44.2% and reorder some loops and policies. Swapping saturation and slew limit does not. A table in Section 4 states, for each conclusion, the conditions under which it was tested and whether it holds.
5. **Context from a short audit.** A short literature audit with a registered protocol, not systematic and coded by one reader, screened 66 candidates and read 12 in full (14 more were available only as abstracts and are not counted). None of the 12 states a slew-rate limit, and none of the 7 whose control law is not purely predictive states the action of the loop; for the 5 predictive controllers that item does not apply. The audit is in the Introduction and the supplement, not in the abstract.

**What the paper does not claim.**
- **The rate trigger is not universally beneficial.** It worsens the slow SIMC loop on the reactor and the Tyreus–Luyben loop on the second plant.
- **The rate-demand heuristic is offered as a heuristic.** It was observed on the reactor without noise and does not transfer to the second plant.
- **The latch is not shown on the second plant.** Its hypotheses are not reached there.
- **The second plant is ours.** It is a heat exchanger built for this study, not a published benchmark.
- **Out of scope:** dynamic (LMI) anti-windup compensators, plant data and hardware tests.

**Relation to our other work.** Two sibling manuscripts by the same authors are in preparation for submission and share only the reactor model and the code base:
- *When Does Nonlinear Model Predictive Control Outperform Robust PID? A Comparative Study under Fouling and Actuator Constraints* (Computers & Chemical Engineering);
- *Thermal Controllability Limits and Cascade Control in Exothermic CSTRs under Cooling Capacity Degradation* (Chemical Engineering Research and Design).

The present manuscript contains no fouling scenario, predictive controller or cascade result, and reuses none of their tables or figures.

**Data and software.** Code, scripts and the CSV files behind every table and figure are in a public repository and will be archived on Zenodo (the DOI is assigned on deposit); every number in the text is generated from them.

**Declarations.** The manuscript is not under consideration elsewhere. The authors used Claude (Anthropic) for coding assistance and language editing, as declared in the manuscript. The authors declare no competing interests.

Sincerely,
Gabriel Marques de Andrade
gmandrade.egm@uesc.br
