# Cover letter — Journal of Process Control

**Manuscript:** Anti-Windup under Amplitude and Slew-Rate Limits in Reverse-Acting Process Loops: An Implementation Study on an Exothermic CSTR

**Authors:** Gabriel Marques de Andrade (corresponding), Elilton Rodrigues Edwards — State University of Santa Cruz (UESC), Brazil

Dear Editor,

We submit the manuscript above for consideration as a regular paper in the *Journal of Process Control*.

**This is not a PID tuning study.** Its subject is the implementation of constraint handling in a process loop: the integrator logic of a controller that acts through a valve limited in amplitude and in slew rate. The six PID controllers are a fixed-gain test bed; their gains come from published rules or one constrained optimization and are not designed, ranked or compared as tuning methods. The tuning-specific material is confined to the Supplementary Material and is not used by the conclusions.

**Contribution.**
1. A diagnosis of a sign error: clamping written for a direct-acting loop and reused in a reverse-acting one freezes the integrator when it must unwind.
2. A proposition that, under stated hypotheses, this sign-blind rule latches the valve at full cooling. The hypotheses are verified on the reactor by simulation, not proved for it.
3. A 2×2 factorial (trigger: amplitude only or amplitude plus slew rate; sign awareness: unconditional or directional) within a seven-policy ablation, which attributes the recovery to the slew-rate trigger.
4. Back-calculation with one tracking constant per loop, chosen by cross-validation on the design step and judged on larger steps.
5. A map over the valve slew limit showing for which loops and valve speeds the slew-rate trigger matters.

**What the paper does not claim.** We do not propose a new anti-windup law. The slew-rate trigger is not universally beneficial: for the slow, well-damped SIMC loop it makes the response worse than no anti-windup at almost every slew limit. We therefore offer a heuristic, not a validated criterion: use the trigger when the loop demands faster valve moves than the slew limit allows. It is model-based and noise-free, and is checked on a second operating point and with a valve deadband. Back-calculation matches the directional rule only without measurement noise. All results come from one reactor model, with one valve model and two operating points. Valve deadband is simulated; stiction, a second process and dynamic (LMI) anti-windup compensators are not. The controller is assumed to know the slew-limited valve position, not to measure it.

**Relation to our other work.** Two sibling manuscripts by the same authors are under review elsewhere and share only the plant model and the code base. *When Does Nonlinear Model Predictive Control Outperform Robust PID? A Comparative Study under Fouling and Actuator Constraints* (Computers & Chemical Engineering) compares nonlinear MPC with two of the PID controllers used here under jacket fouling. *Thermal Controllability Limits and Cascade Control in Exothermic CSTRs under Cooling Capacity Degradation* (Chemical Engineering Research and Design) studies the heat-removal limit and cascade control. The present manuscript contains no fouling scenario, predictive controller or cascade result, and reuses none of their tables or figures.

**Data and software.** Code, scripts and the CSV files behind every table and figure are released; every number in the text is generated from them.

**Declarations.** The manuscript is not under consideration elsewhere. The authors used Claude (Anthropic) for coding assistance and language editing, as declared in the manuscript. The authors declare no competing interests.

Sincerely,
Gabriel Marques de Andrade
gmandrade.egm@uesc.br
