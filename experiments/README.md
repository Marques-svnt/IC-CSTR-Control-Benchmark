# Experimentos Numéricos e Reprodutibilidade Científica — Artigo 1

> **Guia Completo de Execução, Reprodutibilidade e Análise dos Experimentos**  
> Todos os scripts contidos neste diretório foram projetados para serem estritamente determinísticos, totalmente automatizados e reprodutíveis, gerando diretamente as figuras em formato vetorial (PDF) e alta resolução (PNG 300 DPI) e as tabelas em código LaTeX (`booktabs`) que compõem o manuscrito final do **Artigo 1**.

---

## Índice dos Experimentos

| Script | Descrição | Figuras Geradas | Tabelas Geradas | Tempo Aprox. |
|---|---|---|---|---|
| [`exp_01_classical_benchmark.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/experiments/exp_01_classical_benchmark.py) | Benchmark comparativo nominal sob degrau de setpoint | `fig1_classical_benchmark` | `benchmark_table.tex` | ~30 s |
| [`exp_02_robustness_campaign.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/experiments/exp_02_robustness_campaign.py) | Campanha de robustez: Carga, *Fouling*, Ruído e Multi-step | `fig2_disturbance_rejection`<br>`fig3_fouling_sensitivity`<br>`fig5_multistep_tracking` | `disturbance_rejection_table.tex`<br>`fouling_sensitivity_table.tex`<br>`noise_chattering_table.tex`<br>`multistep_tracking_table.tex` | ~3 min |
| [`exp_03_pareto_tuning_sweep.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/experiments/exp_03_pareto_tuning_sweep.py) | Exploração contínua da fronteira de Pareto IAE vs TV ($\tau_c$-sweep e $\lambda$-sweep) | `fig4_pareto_frontier` | `pareto_tradeoff_table.tex` | ~4 min |

Os arquivos de saída são salvos automaticamente em:
* **Figuras:** `Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/figures/`
* **Tabelas:** `Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/tables/`

---

## Detalhamento Técnico de Cada Experimento

### 1. `exp_01_classical_benchmark.py` — Benchmark Nominal
* **Objetivo:** Estabelecer a linha de base comparativa entre os quatro métodos de sintonia em condições ideais de processo.
* **Procedimento Experimental:**
  1. O reator é inicializado no ponto nominal de equilíbrio ($\bar{q}_j = 100.0\text{ L/min}$, $\bar{T} = 344.16\text{ K}$, $\bar{C}_A = 0.1345\text{ mol/L}$).
  2. Um degrau de excitação em malha aberta de $+10.0\text{ L/min}$ é aplicado para identificação do modelo FOPTD via `identify_foptd`.
  3. São sintetizados os controladores PID:
     * Ziegler-Nichols (curva de reação em malha aberta)
     * Cohen-Coon (compensação analítica de atraso)
     * Skogestad SIMC ($\tau_c = 0.40\text{ min}$)
     * Otimizado por Nelder-Mead minimizando ITAE com restrição de sensibilidade máxima $M_s \le 1.6$.
  4. Executa-se uma simulação de malha fechada determinística ($t \in [0, 10]\text{ min}$, $\Delta t = 0.02\text{ min}$) solicitando uma redução na temperatura de setpoint de $\Delta T = -2.0\text{ K}$.
  5. As dinâmicas temporais de temperatura $T(t)$, vazão manipulada de resfriamento $q_j(t)$ e concentração $C_A(t)$ são plotadas e as métricas são tabuladas.

### 2. `exp_02_robustness_campaign.py` — Campanha Exaustiva de Robustez
Avalia o comportamento dos controladores frente a quatro desafios operacionais típicos da indústria química:
1. **Rejeição a Perturbações de Carga Não Medidas (Load Disturbance):**  
   * Em $t = 2.0\text{ min}$: Degrau positivo na temperatura de alimentação da corrente de carga $\Delta T_f = +5.0\text{ K}$.
   * Em $t = 8.0\text{ min}$: Degrau positivo na concentração de alimentação $\Delta C_{Af} = +0.2\text{ mol/L}$ ($+20\%$), aumentando subitamente a geração de calor exotérmico no interior do reator.
2. **Incerteza Paramétrica e Incrustação Térmica (*Fouling*):**  
   Simula o envelhecimento e acúmulo de crostas nas paredes do trocador de calor através da degradação paramétrica de $UA$ de $100\%$ até $60\%$ do valor nominal, em passos de $10\%$. Avalia se o sistema preserva estabilidade ou entra em ciclos-limite induzidos pela saturação de válvula.
3. **Imunidade a Ruído de Medição e Desgaste do Atuador:**  
   Varredura estocástica do desvio padrão do ruído de leitura do termopar $\sigma_{\text{noise}} \in [0.0, 0.5]\text{ K}$ com semente fixa (`seed=42`). Avalia o aumento na métrica $\text{TV}$ (indicativo de desgaste mecânico de gaxetas e hastes de válvulas) decorrente da amplificação de altas frequências pela ação derivativa.
4. **Rastreamento em Ampla Faixa de Operação (Multi-Step Tracking):**  
   Aplica uma sequência de múltiplos degraus alternados:
   * $t \in [0, 5)\text{ min}$: $T_{\text{sp}} = \bar{T} - 2.0\text{ K}$
   * $t \in [5, 10)\text{ min}$: $T_{\text{sp}} = \bar{T} + 4.0\text{ K}$
   * $t \in [10, 15]\text{ min}$: $T_{\text{sp}} = \bar{T} - 5.0\text{ K}$  
   Demonstra como a não-linearidade assimétrica da cinética de Arrhenius degrada o desempenho de controladores sintonizados por modelos lineares locais.

### 3. `exp_03_pareto_tuning_sweep.py` — Fronteira de Pareto Multi-Objetivo
* **Objetivo:** Mapear a fronteira ótima de compromisso (*trade-off*) entre acurácia de controle ($\text{IAE}$) e desgaste físico do atuador ($\text{TV}$).
* **Procedimento:**
  1. **Varredura Contínua do SIMC:** O parâmetro de projeto de malha fechada $\tau_c$ é varrido em 60 pontos no intervalo logarítmico $\tau_c \in [0.015, 2.5]\text{ min}$.
  2. **Otimização Escalarizada Bi-Objetivo:** Otimização numérica direta minimizando:
     $$J(\lambda) = \lambda \frac{\text{IAE}}{\text{IAE}_0} + (1 - \lambda) \frac{\text{TV}}{\text{TV}_0}$$
     para $\lambda \in [0.05, 0.95]$.
  3. **Identificação da Fronteira Não Dominada:** Aplica o algoritmo de Pareto `filter_pareto_front` descartando pontos que violam a restrição de sensibilidade máxima $M_s > 1.6$.
  4. **Ponto de Joelho (*Knee Point*):** Calcula o ponto ótimo na curva com distância euclidiana mínima ao ponto utópico normalizado $(0, 0)$.

---

## Como Reproduzir os Experimentos

### Modo 1: Execução Automatizada via Terminal (PowerShell)

Certifique-se de estar na raiz do projeto com o ambiente virtual ativado:

```powershell
# Ativar o ambiente virtual
.venv\Scripts\Activate.ps1

# Executar Experimento 1 (Benchmark Nominal)
python experiments\exp_01_classical_benchmark.py

# Executar Experimento 2 (Campanha de Robustez)
python experiments\exp_02_robustness_campaign.py

# Executar Experimento 3 (Varredura de Pareto)
python experiments\exp_03_pareto_tuning_sweep.py
```

### Modo 2: Execução Interativa no Spyder 6

O **Spyder 6** é o ambiente IDE recomendado para desenvolvimento científico interativo.

1. **Abrir o Projeto:**
   * Abra o Spyder 6 e vá em **Projects** $\to$ **Open Project...**
   * Selecione a pasta raiz: `C:\Users\biely\OneDrive\Área de Trabalho\2026.2\IC`.
2. **Selecionar Interpretador:**
   * Verifique em **Preferences** $\to$ **Python Interpreter** que o executável selecionado é `.venv\Scripts\python.exe`.
3. **Execução por Células (`# %%`):**
   * Abra, por exemplo, `experiments/exp_01_classical_benchmark.py`.
   * Cada seção principal do script é delimitada por `# %%`, formando blocos de código independentes.
   * Coloque o cursor dentro de uma célula e pressione **`Shift + Enter`** para executar apenas aquele bloco no console interativo IPython e avançar para a próxima célula.
   * Use **`Ctrl + Enter`** para reexecutar a célula atual sem avançar.
4. **Análise de Variáveis no Variable Explorer:**
   * No painel **Variable Explorer** à direita, visualize as variáveis geradas (`df`, `sim_results`, `controllers`, `foptd`).
   * Dê duplo clique em `sim_results` para inspecionar os arrays temporais numéricos de estados e ações de controle.
5. **Visualização de Gráficos no Painel Plots:**
   * Todas as figuras geradas (`plt.figure()`) aparecem automaticamente renderizadas no painel **Plots**.
   * Você pode navegar entre os gráficos anteriores, aplicar zoom e exportar diretamente imagens customizadas.

---

## Protocolo de Reprodutibilidade

Para garantir que qualquer pesquisador no mundo obtenha exatamente os mesmos números decimais apresentados no Artigo 1:
1. **Sementes Aleatórias Fixas:** O ruído estocástico de medição utiliza gerador pseudo-aleatório Numpy com semente explícita (`seed=42`).
2. **Método de Integração Numérica:** Utiliza-se `scipy.integrate.solve_ivp` com método `RK45`, passo máximo limitado e tolerâncias $rtol=10^{-6}$ e $atol=10^{-8}$.
3. **Condições Iniciais Determinísticas:** O estado inicial é sempre calculado pelo solver de ponto de equilíbrio `find_steady_state`, evitando transientes artificiais de partida.
4. **Dependências Congeladas:** Todas as versões exatas das bibliotecas matemáticas estão fixadas em `requirements.txt`.
