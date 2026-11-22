# IC-CSTR-Control-Benchmark

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24449532.svg)](https://doi.org/10.5281/zenodo.24449532)

Simulation code, PID controllers with seven anti-windup policies, campaign scripts, fixed random seeds, generated figures, literature-audit coding, and CSV datasets accompanying the *Journal of Process Control* manuscript:

> **Anti-Windup under Amplitude and Slew-Rate Limits in Reverse-Acting Process Loops: An Implementation Study on an Exothermic CSTR**  
> Gabriel Marques de Andrade, Elilton Rodrigues Edwards — State University of Santa Cruz (UESC)

## Repository Structure

```text
.
├── src/
│   ├── sim_core/            # Non-isothermal CSTR plant, heat exchanger (2nd plant), actuators, RK45/fixed-step integrators, Pydantic schemas
│   ├── classical_control/   # Discrete PID with 7 anti-windup policies, FOPTD identification, analytical & constrained-ITAE tuning, closed-loop runner
│   └── evaluation/          # Tracking/valve metrics (IAE, ITAE, TV, Mp), Pareto frontier, Sobol/Shapley sensitivity, publication plot styles
├── experiments/
│   ├── exp_01_classical_benchmark.py   # Nominal setpoint-tracking benchmark
│   ├── exp_02_robustness_campaign.py   # Disturbance rejection, noise, and parametric robustness
│   ├── exp_03_pareto_tuning_sweep.py   # Multi-objective IAE vs. TV Pareto sweep
│   └── build_paper_assets.py           # Master generator of all CSV datasets, tables, and figures
├── results/jpc/
│   ├── *.csv                           # Complete CSV mirrors backing every table and figure (main text + supplementary)
│   └── figures/*.pdf                   # Publication-grade vector figures
├── repository/
│   ├── literature_audit.csv            # Short literature audit protocol & screening table
│   ├── audit_coding.csv                # Full-text coding of the 12 audited articles
│   └── S2_tuning_extended.tex          # Extended tuning-study tables
├── scripts/
│   └── jpc_numbers.py                  # Deterministic generator of all 418 manuscript macros & condensed LaTeX tables from CSVs
├── tests/                              # Unit and invariant tests (pytest)
├── CITATION.cff                        # Software citation metadata
├── .zenodo.json                        # Zenodo deposit metadata
└── LICENSE                             # MIT License
```

## Installation

Python 3.11+ is required (tested on Python 3.12).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Reproducibility

### 1. Verify tests and code quality

```bash
make test
make lint
```

### 2. Regenerate all manuscript macros and condensed tables from the CSV datasets

```bash
make reproduce-numbers
```

This executes `scripts/jpc_numbers.py`, reading `results/jpc/*.csv` and `repository/*.csv`, and writes the 418 deterministic LaTeX macros (`outputs/jpc/generated/numbers.tex`), the provenance map (`results/jpc/v9_numbers.csv`), and the condensed LaTeX tables (`outputs/jpc/tables/`).

### 3. Re-run simulation campaigns from scratch

```bash
make exp01
make exp02
python3 experiments/build_paper_assets.py
```

All stochastic experiments (measurement noise, 30 realizations per case; Sobol/Shapley global sensitivity) use fixed random seeds declared in the scripts.

## Citation

If you use this software or dataset, please cite it using [`CITATION.cff`](CITATION.cff) or the Zenodo record:

> Marques de Andrade, G., & Rodrigues Edwards, E. (2026). *IC-CSTR-Control-Benchmark: simulation code, controllers and data for anti-windup under actuator limits in an exothermic CSTR* (Version v2.0.1-jpc). Zenodo. https://doi.org/10.5281/zenodo.24449532

## License

Released under the [MIT License](LICENSE).
