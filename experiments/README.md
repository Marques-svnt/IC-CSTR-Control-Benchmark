# Campanhas Experimentais e Reprodutibilidade Numérica — Trilogia CSTR

> **Guia Técnico de Execução, Reprodutibilidade e Análise Numérica**  
> Todos os scripts neste diretório são estritamente determinísticos, totalmente automatizados e reprodutíveis. Eles geram diretamente os dados brutos (`results/*.csv`), figuras vetoriais de alta resolução (`.pdf`) e tabelas em código LaTeX (`booktabs`) que alimentam os três artigos da Elsevier.

---

## Índice das Campanhas Experimentais

| Script | Artigo Alvo | Descrição Técnica | Figuras / Tabelas Geradas | Tempo Médio |
|---|---|---|---|---|
| [`exp_01_classical_benchmark.py`](exp_01_classical_benchmark.py) | **Artigo 1 (JPC)** | Benchmark comparativo nominal sob degrau de setpoint $\Delta T = -2\text{ K}$ | `fig1_classical_benchmark.pdf`<br>`tables/benchmark_table.tex` | ~20 s |
| [`exp_01b_nmpc_oracle_comparison.py`](exp_01b_nmpc_oracle_comparison.py) | **Artigo 2 (CACE)** | Comparação direta entre NMPC-Oracle, NMPC-MHE e PIDs sob incrustação abrupta | `fig_nmpc_oracle_comparison.pdf`<br>`tables/nmpc_oracle_benchmark.tex` | ~45 s |
| [`exp_02_robustness_campaign.py`](exp_02_robustness_campaign.py) | **Artigo 1 (JPC)** | Distúrbios de carga combinados, fouling estático, 1200 Monte Carlo sob ruído e Sobol | `fig2_disturbance_rejection.pdf`<br>`fig_noise_sensitivity.pdf`<br>`fig_sobol_indices.pdf` | ~3 min |
| [`exp_03_pareto_tuning_sweep.py`](exp_03_pareto_tuning_sweep.py) | **Artigo 1 (JPC)** | Varredura contínua de Pareto IAE vs TV ($\tau_c$-sweep em 60 pontos e $\lambda$-sweep) | `fig4_pareto_iae_tv.pdf`<br>`tables/pareto_tradeoff_table.tex` | ~2 min |
| [`exp_04_neural_control_benchmark.py`](exp_04_neural_control_benchmark.py) | **Artigo 2 (CACE)** | Benchmark comparativo de controladores preditivos e redes avançadas | `fig_exp_04_neural_benchmark.png`<br>`results_exp_04_neural_benchmark.csv` | ~1 min |
| [`exp_05_cascade_benchmark.py`](exp_05_cascade_benchmark.py) | **Artigo 3 (ChERD)** | Estrutura de controle em cascata $T \to T_j \to q_j$ sintonizada via SIMC sequencial | `fig6_cascade_comparison.pdf`<br>`tables/cascade_comparison_table.tex` | ~30 s |
| [`exp_06_unstable_saddle_and_fouling.py`](exp_06_unstable_saddle_and_fouling.py) | **Artigo 3 (ChERD)** | Operação no ponto de sela instável ($\lambda_1 > 0$), cinética contínua de fouling e $t_{\text{runaway}}$ | `fig1_van_heerden.png`<br>`fig4_fouling_runaway.png`<br>`cherd_fouling.csv` | ~40 s |
| [`build_paper_assets.py`](build_paper_assets.py) | **Trilogia Completa** | Script mestre que executa a regeneração integral de tabelas e figuras para os 3 periódicos | Regenera `papers/*/figures/` e `papers/*/tables/` | ~6 min |

---

## Diretórios de Saída e Espelhamento

Para evitar sobrescrita de dados entre os artigos, cada publicação possui um espelho isolado em `results/`:
* **Artigo 1 (JPC):** `results/jpc/*.csv` $\to$ `papers/01_journal_of_process_control/tables/`
* **Artigo 2 (CACE):** `results/cace/*.csv` $\to$ `papers/02_computers_chemical_engineering/tables/`
* **Artigo 3 (ChERD):** `results/cherd/*.csv` $\to$ `papers/03_chemical_engineering_research_design/tables/`

---

## Como Executar as Campanhas via Terminal

Certifique-se de que o ambiente virtual está ativo:

```bash
# Ativação do ambiente virtual
source .venv/bin/activate

# 1. Executar Benchmark Nominal (Artigo 1)
python experiments/exp_01_classical_benchmark.py

# 2. Executar Campanha NMPC vs PID (Artigo 2)
python experiments/exp_01b_nmpc_oracle_comparison.py

# 3. Executar Campanha de Robustez e Monte Carlo (Artigo 1)
python experiments/exp_02_robustness_campaign.py

# 4. Executar Varredura de Pareto Contínua (Artigo 1)
python experiments/exp_03_pareto_tuning_sweep.py

# 5. Executar Ponto de Sela e Cinética de Fouling (Artigo 3)
python experiments/exp_06_unstable_saddle_and_fouling.py

# 6. Reconstruir Todos os Assets da Trilogia de Uma Só Vez:
python experiments/build_paper_assets.py
```

---

## Regra de Ouro: Anti-Mocking Científico

Nenhum número presente nas tabelas em `papers/**/tables/*.tex` ou nos textos dos manuscritos é fixado manualmente (*hardcoded*). Todas as métricas $\text{IAE}$, $\text{ITAE}$, $\text{TV}$, $M_p$, $t_s$ e $M_s$ fluem diretamente dos CSVs gerados pelos scripts acima, garantindo conformidade estrita com o padrão de integridade editorial dos periódicos da Elsevier.
