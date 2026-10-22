# Manuscritos Científicos — Trilogia Elsevier Q1 (`cas-dc.cls`)

Este diretório contém os três artigos científicos completos resultantes da pesquisa de Iniciação Científica (PROIC/UESC/FAPESB/CNPq), diagramados no padrão oficial de duas colunas da **Elsevier (`\documentclass[a4paper,fleqn]{cas-dc}`)**.

---

## Estrutura dos Manuscritos

```
papers/
├── 01_journal_of_process_control/          # Artigo 1: Benchmark PID Robusto sob Saturação
│   ├── main.tex, highlights.tex, references.bib
│   ├── sections/                           # 01_intro, 02_plant, 03_pid, 04_results, 05_concl
│   ├── tables/                             # Tabelas LaTeX (booktabs)
│   ├── figures/                            # Figuras vetoriais de alta resolução (PDF)
│   ├── ready-to-overleaf/                  # Pasta autossuficiente para Overleaf
│   ├── ready_to_overleaf.zip               # Pacote ZIP pronto para upload direto
│   └── main.pdf                            # PDF compilado (11 páginas em duas colunas)
│
├── 02_computers_chemical_engineering/       # Artigo 2: NMPC vs PID Robusto sob Fouling
│   ├── main.tex, highlights.tex, references.bib
│   ├── sections/                           # 01_intro, 02_nmpc, 03_baseline, 04_results, 05_concl
│   ├── tables/                             # Tabelas LaTeX de NMPC, MHE e tempos computacionais
│   ├── figures/                            # Figuras vetoriais de trajetórias e incrustação
│   ├── ready-to-overleaf/                  # Pasta autossuficiente para Overleaf
│   ├── ready_to_overleaf.zip               # Pacote ZIP pronto para upload direto
│   └── main.pdf                            # PDF compilado (10 páginas em duas colunas)
│
└── 03_chemical_engineering_research_design/ # Artigo 3: Ponto de Sela Instável & Cascata SIMC
    ├── main.tex, highlights.tex, references.bib
    ├── sections/                           # 00_abstract, 01_intro, 02_model, 03_control, etc.
    ├── tables/                             # Tabelas LaTeX de autovalores, fouling e choques
    ├── figures/                            # Diagramas de Van Heerden e retratos de fase
    ├── ready-to-overleaf/                  # Pasta autossuficiente para Overleaf
    ├── ready_to_overleaf.zip               # Pacote ZIP pronto para upload direto
    └── main.pdf                            # PDF compilado (10 páginas em duas colunas)
```

---

## 1. Mapeamento dos Artigos e Periódicos Alvo

| Artigo | Periódico Alvo | Título do Manuscrito | Foco e Contribuições Principais | Extensão |
|---|---|---|---|---|
| **Artigo 1** | *Journal of Process Control* (JPC) | *Robust PID Tuning under Actuator Saturation in Nonlinear Exothermic CSTRs: Performance, Anti-Windup and Sensitivity Trade-offs* | Benchmark de 8 PIDs (ZN, CC, TL, AMIGO, 2-DOF, SIMC, Nelder-Mead $M_s \le 1.6$), anti-windup direcional sob slew-rate, fronteira de Pareto contínua e 1200 Monte Carlo com análise de Sobol. | 11 págs |
| **Artigo 2** | *Computers & Chemical Engineering* (CACE) | *When Does Nonlinear Model Predictive Control Outperform Robust PID? A Comparative Study under Fouling and Actuator Constraints* | NMPC-Oracle vs. NMPC com estimador MHE ($\mathbf{x}_a = [C_A, T, T_j, \alpha_{UA}]^T$) contra AMIGO e Ótimo ITAE sob perda abrupta de troca térmica e perturbações não medidas. | 10 págs |
| **Artigo 3** | *Chemical Engineering Research and Design* (ChERD) | *Thermal Controllability Limits and Cascade Control in Exothermic CSTRs under Cooling Capacity Degradation* | Estabilização no ponto de sela instável ($\lambda_1 = +0.744\text{ min}^{-1}$), cinética contínua de fouling $d(UA)/dt = -\kappa_{\text{foul}} r_A (UA - UA_{\min})$ e tempo crítico até runaway ($t_{\text{runaway}}$) com controle em cascata SIMC. | 10 págs |

---

## 2. Como Compilar Localmente via Terminal

Para compilar qualquer um dos manuscritos localmente com `pdfLaTeX`:

```bash
# Compilar Artigo 1
cd papers/01_journal_of_process_control
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex

# Compilar Artigo 2
cd ../02_computers_chemical_engineering
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex

# Compilar Artigo 3
cd ../03_chemical_engineering_research_design
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

---

## 3. Upload Imediato no Overleaf

Cada pasta possui o arquivo `ready_to_overleaf.zip`.
Esse arquivo compactado contém exclusivamente os arquivos de código-fonte, tabelas, figuras PDF reais (sem links simbólicos) e arquivos de estilo Elsevier (`cas-dc.cls` e `cas-common.sty`).

Basta fazer o upload do ZIP diretamente no Overleaf:
* **Zero erros de compilação.**
* **Zero referências indefinidas (`??`).**
* **Numeração de páginas rigorosamente correta** (graças à correção do hook de final de documento `\clearpage`).
