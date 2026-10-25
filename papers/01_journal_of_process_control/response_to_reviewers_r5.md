# Response to the reviewers — fifth round (draft)

Manuscript: *Anti-Windup under Amplitude and Slew-Rate Limits in Reverse-Acting Process Loops: An Implementation Study on an Exothermic CSTR* (v6).

We thank the reviewers for the detailed reports and for reproducing our numbers independently. All numbers quoted in the revised main text are now LaTeX macros generated from the CSV files that the released code writes (`scripts/jpc_v6_numbers.py`); `scripts/check_text_numbers.py` regenerates them and fails if the manuscript is stale. Section and table numbers below refer to the revised manuscript (main text) and to the Supplementary Material (S1–S6).

## Mandatory requirements

| # | Requirement | Action | Where |
|---|---|---|---|
| 1 | Scope: reframe around anti-windup and actuator constraints; justify why this is not a PID tuning study; cut or move pure tuning content | New title, abstract, keywords, highlights, Introduction and conclusions. The Introduction states that the six fixed-gain controllers are a test bed and are not designed or compared as tuning methods. The ITAE design under an M_s bound and its cost, the model-error test of that design, out-of-sample steps, setpoint weighting, FOPTD-versus-plant margins, the Pareto/SIMC locus, the derivative-filter study, the full noise campaign, the replicated load runs and the Sobol/Shapley analysis were moved verbatim to the Supplementary Material and are not used by the conclusions. The cover letter carries the scope justification | Title; abstract; Sec. 1 (2nd paragraph), 1.1, 1.2; Sec. 5; Supplementary S1–S6; cover letter |
| 2 | Length: about 12 pages, or a written justification | 25 → 13 pages in the cas-dc template, including the highlights page the template adds; about 4,500 words of text and 14 floats (about 6,600 words by the guide's 150-words-per-float rule, nominal 7,500) | Whole manuscript |
| 3 | Data and software with DOI, cited as a reference | Software reference in the format of the Guide for Authors, cited in the data statement; README reproduction recipe, `CITATION.cff` and `.zenodo.json` prepared. **The Zenodo DOI will be inserted after deposit** (placeholder in the reference) | Data and code availability; reference andrade2026software |
| 4 | References: order of appearance, DOIs, verify [18]–[22] and [29]–[33] | A script checks that references are numbered in first-citation order (31 in order; the apparent disorder came from text extraction of the two-column PDF). Journal names abbreviated by the LTWA. All references with DOI checked against Crossref (title, first author, year, volume, first page); the ten references [18]–[22] and [29]–[33] of v5 were confirmed. Four of them are no longer cited, because they supported the tuning content now in the supplement | Reference list; `scripts/check_citation_order.py`, `scripts/verify_bib_crossref.py` |
| 5 | Cover letter with scope and length justification and the relation with companion manuscripts | Written | Cover letter |

## Recommended requirements

| # | Recommendation | Action | Where |
|---|---|---|---|
| 1 | T_t^cv as main criterion; curve outside [T_d, T_i]; TV and overshoot | T_t^cv (chosen on the design step, judged on ±5 K) leads in the abstract, highlight 3, Sec. 4.4 and conclusion 3; T_t^mm is kept as an in-sample confirmation. The design-step choice was repeated without the range restriction: for ZN, CC and SIMC the minimum leaves the range, and the worst ratio on ±5 K does not improve in any loop. A new table compares IAE, TV and overshoot: for ZN and CC back-calculation with T_t^cv moves the valve less and overshoots less in 5 of 6 cases, for SIMC it moves the valve 20–38% more | Sec. 4.4, Fig. 3, Tables 6 and 7 |
| 2 | Model error with physical perturbations; qualify conclusion 3 | The model-error test belongs to the exact-loop ITAE design, which moved to the supplement; the sentence of the former conclusion 3 is no longer in the main text. The physical-perturbation test was not run | Supplementary S2 |
| 3 | Intervals for the Shapley effects, or remove Sobol/Shapley | Sobol and Shapley moved to the supplement, which, as Reviewer 3 noted, removes the requirement from the main text; the intervals were not added | Supplementary S6 |
| 4 | Second independent process | Not done; stated as a limitation and as future work. The ablation at a second operating point of the same reactor is kept | Sec. 4.6, 4.9, 5 |
| 5 | Stiction; deadband in robustness | Deadband kept for the anti-windup policies; stiction not modelled (stated) | Sec. 4.6, 4.9 |
| 6 | Condense Tables 3, 13–15 and the noise tables; bootstrap intervals in Tables 7–8 | Gains, nominal metrics and robustness merged into one test-bed table; the noise tables moved to the supplement. The back-calculation tables are deterministic, so no sampling interval applies | Table 3; Supplementary S4 |
| 7 | Highlight 4 ("11% lower ITAE") | That highlight belonged to the tuning content and was replaced | Highlights |

## Corrections found during the revision

- The value of I* after Proposition 1 was wrong in v5 (“≈ 300 L/min”); it is 945 L/min for ZN and 1050 L/min for CC, computed from the plant model and the gains.
- The derivative-filter study in the supplement quoted travel values from a run that preceded the alignment of its random seeds with the noise campaign; the text now quotes the current CSV (the percentages are unchanged).
- Table 1 overflowed into the second column, and three equations exceeded the column width; fixed.
