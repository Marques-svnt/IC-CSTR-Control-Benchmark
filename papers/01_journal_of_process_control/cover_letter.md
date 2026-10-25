# Cover letter — Journal of Process Control

**Manuscript:** Anti-Windup under Amplitude and Slew-Rate Limits in Reverse-Acting Process Loops: An Implementation Study on an Exothermic CSTR

**Authors:** Gabriel Marques de Andrade (corresponding), Elilton Rodrigues Edwards — State University of Santa Cruz (UESC), Brazil

Dear Editor,

We submit the manuscript above for consideration as a regular paper in the *Journal of Process Control*.

**Scope.** The Guide for Authors excludes PID tuning and its variants from the advanced design methods covered by the journal, and this manuscript is not a PID tuning study. Its subject is the implementation of constraint handling in process control loops: the anti-windup logic that accompanies a controller acting through a valve limited in amplitude and in slew rate. In a reverse-acting loop a common implementation error, which reuses the freeze condition written for direct-acting loops, latches the valve at its stop; we prove this in a proposition that holds for any reverse-acting loop around an open-loop-stable plant, show the mechanism on the temperature loop of an exothermic CSTR, and map, over the valve slew limit, when a slew-rate-aware trigger is needed. The six PID controllers are a test bed: their gains are fixed by published rules or by one constrained optimization and are not designed, ranked or compared as tuning methods. All analyses that concern the tunings themselves (a design-model robustness constraint, setpoint weighting, a tracking-error versus valve-travel locus, the derivative-filter coefficient and a global sensitivity analysis) were moved to the Supplementary Material and are not used by the conclusions. We submit under "control applications", as an analysis of how the implementation of actuator-constraint handling can decide the verdict on a process control loop.

**Length.** The manuscript has 12 pages in the double-column template, including the highlights page, within the nominal length of a regular paper.

**Relation to the anti-windup literature.** We do not claim a new anti-windup law. Back-calculation, conditional integration and LMI-based compensators for magnitude and rate saturation are established; Section 1.1 and Table 1 place them side by side, and the rule we adopt is the sign-of-increment form of conditional integration evaluated on the slew-limited valve position. What we add is the proposition on the latch of sign-blind clamping, a seven-policy ablation in which the controller gains are held fixed (three setpoint steps, a load profile, a valve deadband and a second operating point), a regime map over slew limits of 20 to 320 L/min², a comparison with back-calculation using one tracking constant per loop chosen by a declared criterion, an account of the noise-to-valve gain through |K_p|(1+N), and a five-item checklist for reporting the anti-windup logic.

**Relation to the companion manuscripts.** [Titles and journals to be confirmed by the authors.] Two sibling manuscripts by the same authors are under review elsewhere and share only the plant model and the code base: *When Does Nonlinear Model Predictive Control Outperform Robust PID? A Comparative Study under Fouling and Actuator Constraints* (Computers & Chemical Engineering) compares nonlinear model predictive control with two of the PID controllers used here under jacket fouling, and *Thermal Controllability Limits and Cascade Control in Exothermic CSTRs under Cooling Capacity Degradation* (Chemical Engineering Research and Design) studies the heat-removal limit of the reactor and cascade control. The present manuscript contains no fouling scenario, no predictive controller and no cascade result, and does not reuse their tables or figures.

**Limits we state.** One reactor model and one valve model, two operating points; deadband simulated, stiction not; dynamic anti-windup compensators not compared (Section 4.9).

**Data and software.** All code, scripts and the CSV file behind every table and figure are released; every number in the text is a macro generated from those files. [DOI of the archived release to be inserted after deposit.]

**Declarations.** The manuscript is not under consideration elsewhere. The authors used Claude (Anthropic) for coding assistance and language editing, as declared in the manuscript. The authors declare no competing interests.

Sincerely,
Gabriel Marques de Andrade
gmandrade.egm@uesc.br
