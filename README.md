# IC — Controle Inteligente de Processos Químicos (PROIC/UESC)
## Artigo 1: Benchmark Abrangente de Sintonias PID em Reator CSTR Não-Linear

> **Projeto de Iniciação Científica (PROIC)**  
> **Instituição:** Universidade Estadual de Santa Cruz (UESC) — Departamento de Ciências Exatas e Tecnológicas (DCET) — Colegiado de Engenharia Química  
> **Orientador:** Prof. Dr. Elilton Rodrigues Edwards  
> **Pesquisador Bolsista / Autor:** Gabriel Marques de Andrade  
> **Edital:** PROIC/FAPESB/CNPq (Edital 34/2026)  
> **Documento Base / Tese:** `archive/legacy_drafts/Tese.pdf` (local, fora do Git) — *"Contornabilidade, Saturação de Atuador e Trade-offs de Robustez no Controle PID Clássico de CSTRs Exotérmicos Altamente Não Lineares"*  
> **Status:** ✅ **Artigo 1 Finalizado (Camera-Ready para Submissão) & Tese Concluída**

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: Pytest](https://img.shields.io/badge/tests-56%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![Coverage: 75%](https://img.shields.io/badge/coverage-75%25-green.svg)](https://coverage.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

---

## Sumário Executivo

Este repositório abriga o código-fonte, experimentos numéricos, testes automatizados e o artigo científico completo referente ao **Artigo 1** da trilogia do projeto PROIC/UESC:

> **"A Comprehensive Benchmark on Classical PID Tuning Strategies for Highly Non-linear CSTR: Robustness, Actuator Saturation, and Multi-Objective Trade-offs"**  
> *Artigo submetido / pronto para submissão (Journal of Process Control / CBA 2026).*

O projeto desenvolve uma infraestrutura científica modular e estritamente reprodutível em Python para simulação fenomenológica de um Reator Contínuo de Mistura (CSTR) não-isotérmico com reação exotérmica de primeira ordem ($A \to B$), modelado via cinético de Arrhenius altamente não-linear e dinâmica térmica de camisa de resfriamento.

O estudo avalia exaustivamente quatro abordagens de projeto e sintonia de controladores PID industriais:
1. **Ziegler-Nichols em Malha Aberta (Curva de Reação)**
2. **Cohen-Coon (Compensação para sistemas com tempo morto)**
3. **Skogestad SIMC (Simple Internal Model Control)**
4. **Otimização Numérica Não-Linear Constrita (Nelder-Mead minimizando ITAE com restrição de sensibilidade máxima $M_s \le 1.6$)**

As estratégias são comparadas em condições nominais de rastreamento de setpoint, rejeição de distúrbios de carga não medidos (choques de temperatura e concentração de alimentação), degradação por incerteza paramétrica/incrustação (*fouling* no trocador de calor de até 40%), presença de ruído de medição estocástico e exploração contínua da fronteira de Pareto multi-objetivo entre acurácia de rastreamento ($\text{IAE}$) e desgaste físico do atuador ($\text{TV}$).

---

## Modelagem Fenomenológica do CSTR

```
           Alimentação de Carga
             (q, C_Af, T_f)
                   │
                   ▼
         ┌──────────────────┐
         │                  │ ◄── Camisa de Resfriamento
         │   Reator CSTR    │     (V_j, rho_j*cp_j)
         │    (V, rho*cp)   │
         │                  │ ──── Vazão de fluido refrigerante (q_j)
         │   A ───k(T)───> B│      Temperatura de entrada (T_jf)
         │                  │
         └─────────┬────────┘
                   │
                   ▼
            Corrente de Saída
              (q, C_A, T)
```

### 1. Balanço Material da Espécie Reagente ($C_A$)

Assumindo volume de reação líquido constante $V$ e mistura perfeita:

$$\frac{d C_A(t)}{dt} = \frac{q}{V}\left(C_{Af} - C_A(t)\right) - r_A(C_A, T)$$

onde a taxa de consumo da espécie $A$ é dada por cinética de primeira ordem:

$$r_A(C_A, T) = k(T) \cdot C_A(t)$$

### 2. Cinética Não-Linear de Arrhenius

A dependência térmica da velocidade de reação introduz forte não-linearidade exponencial:

$$k(T) = k_0 \exp\left(-\frac{E}{R \cdot T(t)}\right)$$

onde $k_0$ é o fator pré-exponencial e $E/R$ é a energia de ativação normalizada pela constante universal dos gases.

### 3. Balanço de Energia Térmica no Reator ($T$)

Considerando entalpia de reação exotérmica $\Delta H < 0$ e transferência térmica através da parede metálica com coeficiente global $UA$:

$$\frac{d T(t)}{dt} = \frac{q}{V}(T_f - T(t)) + \frac{(-\Delta H)}{\rho c_p} k(T) C_A(t) - \frac{UA}{V \rho c_p}(T(t) - T_j(t))$$

### 4. Balanço de Energia Térmica na Camisa de Resfriamento ($T_j$)

Considerando a camisa perfeitamente agitada de volume $V_j$, alimentada com vazão manipulada $q_j(t)$ e temperatura de suprimento $T_{jf}$:

$$\frac{d T_j(t)}{dt} = \frac{q_j(t)}{V_j}(T_{jf} - T_j(t)) + \frac{UA}{V_j \rho_j c_{pj}}(T(t) - T_j(t))$$

---

## Parâmetros Físico-Químicos Nominais

Os parâmetros nominais foram selecionados com base no benchmark acadêmico consagrado da literatura de controle de processos químicos (Seborg et al., Ogunnaike & Ray):

| Parâmetro | Descrição | Valor | Unidade |
|---|---|---|---|
| $q$ | Vazão volumétrica da corrente de processo | $100.0$ | $\text{L/min}$ |
| $V$ | Volume da mistura reacional no reator | $100.0$ | $\text{L}$ |
| $k_0$ | Fator pré-exponencial de Arrhenius | $7.2 \times 10^{10}$ | $\text{min}^{-1}$ |
| $E/R$ | Energia de ativação normalizada | $8750.0$ | $\text{K}$ |
| $-\Delta H$ | Calor exotérmico da reação | $5.0 \times 10^{4}$ | $\text{cal/mol}$ |
| $\rho c_p$ | Capacidade calorífica volumétrica do reator | $500.0$ | $\text{cal/(L}\cdot\text{K)}$ |
| $UA$ | Coeficiente global de troca térmica $\times$ Área | $5.0 \times 10^{4}$ | $\text{cal/(min}\cdot\text{K)}$ |
| $V_j$ | Volume da camisa de resfriamento | $20.0$ | $\text{L}$ |
| $\rho_j c_{pj}$ | Capacidade calorífica volumétrica da camisa | $500.0$ | $\text{cal/(L}\cdot\text{K)}$ |
| $C_{Af}$ | Concentração de reagente na alimentação | $1.0$ | $\text{mol/L}$ |
| $T_f$ | Temperatura da corrente de alimentação | $350.0$ | $\text{K}$ |
| $T_{jf}$ | Temperatura do refrigerante de alimentação | $300.0$ | $\text{K}$ |

### Ponto de Operação Nominal em Regime Permanente ($\bar{x}_{ss}$)

Resolvendo o sistema não-linear residual $f(\bar{x}_{ss}, \bar{q}_{j,ss}) = 0$ via solver de Powell híbrido (`scipy.optimize.root`) para a vazão nominal $\bar{q}_j = 100.0\text{ L/min}$:
* Concentração de reagente: $\bar{C}_A = 0.1345\text{ mol/L}$
* Temperatura do reator: $\bar{T} = 344.16\text{ K}$
* Temperatura da camisa: $\bar{T}_j = 330.43\text{ K}$

---

## Identificação FOPTD e Sintonias PID

A identificação paramétrica é conduzida através de um ensaio em malha aberta aplicando um degrau positivo de vazão de resfriamento $\Delta q_j = +10.0\text{ L/min}$ a partir do ponto nominal. A dinâmica térmica do reator é ajustada ao modelo de Primeira Ordem com Tempo Morto (FOPTD):

$$G(s) = \frac{\Delta T(s)}{\Delta q_j(s)} = \frac{K_p \, e^{-\theta s}}{\tau s + 1}$$

Parâmetros identificados por mínimos quadrados não-lineares:
* Ganho estático: $K_p \approx -0.135\text{ K / (L/min)}$ (processo de ação reversa: aumentar resfriamento diminui temperatura)
* Constante de tempo: $\tau \approx 0.380\text{ min}$
* Tempo morto aparente: $\theta \approx 0.095\text{ min}$
* Razão de controlabilidade: $\theta / \tau \approx 0.25$ (atraso moderado)

### 1. Ziegler-Nichols (Curva de Reação em Malha Aberta)
Fórmula empírica clássica baseada na inclinação máxima e atraso aparente:
$$K_p = \text{sgn}(K) \frac{1.2 \, \tau}{|K| \, \theta}, \quad T_i = 2.0 \, \theta, \quad T_d = 0.5 \, \theta$$

### 2. Cohen-Coon (Compensação para Razões $\theta / \tau$)
Desenvolvido para compensar atrasos de transporte significativos:
$$K_p = \text{sgn}(K) \frac{\tau}{|K| \, \theta} \left(\frac{4}{3} + \frac{\theta}{4 \tau}\right)$$
$$T_i = \theta \frac{32 + 6(\theta/\tau)}{13 + 8(\theta/\tau)}, \quad T_d = \theta \frac{4}{11 + 2(\theta/\tau)}$$

### 3. Skogestad SIMC (Simple Internal Model Control)
Baseado no cancelamento analítico do polo dominante e controle por modelo interno com parâmetro de projeto de malha fechada $\tau_c$:
$$K_p = \text{sgn}(K) \frac{1}{|K|} \frac{\tau}{\tau_c + \theta}, \quad T_i = \min\left(\tau, \, 4(\tau_c + \theta)\right), \quad T_d = 0.33 \, \theta$$
*Neste benchmark, adotou-se $\tau_c = 0.40\text{ min}$, priorizando resposta suave e excelente robustez.*

### 4. Otimização Numérica Não-Linear Constrita (Nelder-Mead com $M_s \le 1.6$)
Minimização direta do critério de desempenho integral avaliado sobre a planta não-linear sujeita a restrições de robustez em frequência:

$$\min_{K_p, T_i, T_d} \quad J = \int_0^{t_{\text{sim}}} t \cdot |e(t)| \, dt + \gamma_{\text{penalty}} \max(0, M_s - 1.6)^2$$

onde a sensibilidade máxima $M_s = \|S(j\omega)\|_\infty$ é obtida a partir da função de transferência de sensibilidade de malha fechada $S(s) = [1 + G(s)C(s)]^{-1}$:

$$M_s = \max_{\omega \in [10^{-3}, 10^2]} \left| \frac{1}{1 + G(j\omega) C_{\text{PID}}(j\omega)} \right|$$

---

## Métricas de Avaliação Acadêmica e Industrial

Para garantir rigor editorial compatível com periódicos de alto impacto (IEEE Transactions / Journal of Process Control), são computadas 7 métricas quantitativas:

1. **Integral do Erro Absoluto (IAE):**  
   $$\text{IAE} = \int_0^{t_f} |r(t) - y(t)| \, dt$$
2. **Integral do Erro Absoluto Ponderado no Tempo (ITAE):**  
   $$\text{ITAE} = \int_0^{t_f} t \cdot |r(t) - y(t)| \, dt$$
3. **Integral do Erro Quadrático (ISE):**  
   $$\text{ISE} = \int_0^{t_f} (r(t) - y(t))^2 \, dt$$
4. **Variação Total da Ação de Controle (TV):** Métrica fundamental de desgaste de válvulas e atuadores:  
   $$\text{TV} = \sum_{k=1}^N |u_k - u_{k-1}|$$
5. **Pico Máximo de Sobressinal ($M_p$):**  
   $$M_p = \frac{\max_t y(t) - r_f}{|r_f - y_0|} \times 100\%$$
6. **Tempo de Acomodação ($t_s$):** Tempo a partir do qual $|y(t) - r_f| \le 0.02 |r_f - y_0|$ de forma contínua.
7. **Sensibilidade Máxima de Robustez ($M_s$):** Margem de estabilidade no plano complexo inverso (distância mínima ao ponto crítico $-1 + j0$). Recomenda-se industrialmente $1.2 \le M_s \le 1.6$ para processos químicos não-lineares.

---

## Resultados Quantitativos do Artigo 1

### Tabela I: Benchmark de Rastreamento Nominal (Degrau de Setpoint $\Delta T = -2.0\text{ K}$)

| Estratégia de Sintonia | $K_p$ | $T_i$ (min) | $T_d$ (min) | IAE | ITAE | TV (L/min) | $M_p$ (%) | $t_s$ (min) | $M_s$ |
|---|---|---|---|---|---|---|---|---|---|
| **Ziegler-Nichols** | $-44.56$ | $0.19$ | $0.047$ | $104.12$ | $666.91$ | $490.3$ | $842.5$ | *Não acomoda* | $1.37$ |
| **Cohen-Coon** | $-50.86$ | $0.22$ | $0.033$ | $102.67$ | $666.90$ | $476.8$ | $842.5$ | *Não acomoda* | $1.50$ |
| **Skogestad SIMC** | $-7.03$ | $0.64$ | $0.031$ | $1.09$ | $0.48$ | **20.9** | **2.1** | $1.98$ | **1.09** |
| **ITAE Ótimo ($M_s \le 1.6$)** | $-14.21$ | $1.00$ | $0.001$ | **0.89** | **0.31** | $44.0$ | $4.8$ | **1.28** | $1.24$ |

### Tabela II: Rejeição a Distúrbios de Carga Combinados ($\Delta T_f = +5\text{ K}$ em $t=2\text{ min}$, $\Delta C_{Af} = +20\%$ em $t=8\text{ min}$)

| Estratégia de Sintonia | IAE | ITAE | TV (L/min) | Desvio de Pico (K) | Abertura Máx. Válvula (L/min) |
|---|---|---|---|---|---|
| **Ziegler-Nichols** | $172.32$ | $1665.63$ | $971.0$ | $56.47$ | $300.0$ (Saturado) |
| **Cohen-Coon** | $120.19$ | $1084.35$ | $932.8$ | $43.31$ | $300.0$ (Saturado) |
| **Skogestad SIMC** | $17.71$ | $158.26$ | **739.2** | **7.35** | $294.5$ |
| **ITAE Ótimo ($M_s \le 1.6$)** | **14.01** | **119.40** | $758.0$ | **7.33** | $300.0$ |

### Tabela III: Sensibilidade ao Fouling Térmico (Degradação de $UA$ de $100\%$ a $60\%$)

| Estratégia | $UA / UA_{\text{nom}}$ | IAE | ITAE | TV (L/min) | Sobressinal $M_p$ (%) |
|---|---|---|---|---|---|
| **Skogestad SIMC** | $100\%$ | $1.42$ | $2.86$ | $450.5$ | $6.9$ |
| **Skogestad SIMC** | $80\%$ | $5.06$ | $7.39$ | $455.0$ | $5.9$ |
| **Skogestad SIMC** | $60\%$ | $30.12$ | $115.20$ | $226.9$ | $0.0$ |
| **ITAE Ótimo ($M_s \le 1.6$)** | $100\%$ | **1.25** | **2.68** | $490.3$ | $8.8$ |
| **ITAE Ótimo ($M_s \le 1.6$)** | $80\%$ | **3.87** | **6.05** | $496.8$ | $5.5$ |
| **ITAE Ótimo ($M_s \le 1.6$)** | $60\%$ | **29.74** | **113.93** | **199.7** | $0.0$ |
| **Ziegler-Nichols** | $100\%$ | $96.29$ | $631.76$ | $542.0$ | $841.6$ (*Ciclo Limite*) |
| **Cohen-Coon** | $100\%$ | $94.60$ | $630.33$ | $524.4$ | $841.6$ (*Ciclo Limite*) |

### Conclusões Científicas Centrais do Artigo 1
1. **Falha Crítica dos Métodos Clássicos Empíricos (ZN e CC):** Embora ZN e CC produzam ganhos formalmente válidos para o modelo FOPTD linearizado, na planta física real seus ganhos agressivos ($K_p \approx -45$ a $-51$) empurram a válvula repetidamente contra as saturações físicas ($0$ a $300\text{ L/min}$). A interação entre o windup residual e a cinética exponencial gera ciclos-limite violentos com oscilações térmicas inaceitáveis de até $\pm 56\text{ K}$.
2. **Superioridade e Elegância do Skogestad SIMC:** Com um único parâmetro de sintonia ($\tau_c$), o SIMC produziu um erro IAE $99\%$ menor que ZN/CC, com uma redução de **$95.7\%$ na Variação Total do Atuador (TV = 20.9 vs 490.3 L/min)**, eliminando o estresse mecânico da válvula de controle.
3. **Desempenho Ótimo com Robustez Garantida:** O controlador ITAE Ótimo com restrição $M_s \le 1.6$ superou todas as alternativas em velocidade de convergência ($t_s = 1.28\text{ min}$) mantendo excelente margem de robustez em malha fechada ($M_s = 1.24$).

---

## Estrutura Limpa e Modular do Repositório

O repositório é rigorosamente estruturado, sem arquivos temporários ou pastas de exercícios:

```
IC/
├── .gitignore                        # Regras limpas para Python, Spyder, LaTeX e temporários
├── pyproject.toml                    # Metadados do pacote cstr_control_research e configs ruff/pytest
├── requirements.txt                  # Dependências com versões estritas
├── README.md                         # Este documento: documentação técnica mestre do projeto
│
├── src/                              # Pacote Python 'src' (Código de Produção Científica)
│   ├── README.md                     # Documentação da arquitetura e APIs internas do pacote
│   ├── sim_core/                     # EDOs do reator CSTR, dinâmica de atuadores e integrador ODE
│   │   ├── cstr_plant.py             # Parâmetros físicos, derivadas não-lineares, Jacobiana e ponto SS
│   │   ├── actuators.py              # Modelo de válvula com saturação física e slew rate limit
│   │   └── integrator.py             # Integrador numérico RK45 desacoplado (solve_ivp)
│   ├── classical_control/            # Algoritmos de controle clássico e sintonias
│   │   ├── foptd.py                  # Identificação de Primeira Ordem com Tempo Morto
│   │   ├── pid_controller.py         # PID paralelo industrial com anti-windup e filtro N
│   │   ├── tuning_analytical.py      # Fórmulas analíticas ZN, CC e Skogestad SIMC
│   │   ├── tuning_optimization.py    # Otimização Nelder-Mead com restrição de sensibilidade Ms <= 1.6
│   │   └── closed_loop.py            # Motor de simulação em malha fechada
│   └── evaluation/                   # Métricas de desempenho e pós-processamento gráfico
│       ├── metrics.py                # IAE, ITAE, ISE, TV, Mp, ts e tr
│       ├── pareto.py                 # Filtragem e sumarização de fronteira de Pareto (IAE vs TV)
│       └── plot_styles.py            # Configuração de estilo de publicação IEEE Transactions
│
├── experiments/                      # Scripts de experimentos reprodutíveis
│   ├── README.md                     # Guia passo a passo dos experimentos e reprodutibilidade
│   ├── exp_01_classical_benchmark.py # Experimento 1: Benchmark nominal e Tabela I
│   ├── exp_02_robustness_campaign.py # Experimento 2: Distúrbios, Fouling, Ruído e Tabelas II, III
│   └── exp_03_pareto_tuning_sweep.py # Experimento 3: Varredura de Pareto e fronteira ótima
│
├── tests/                            # Suíte de testes unitários (56 testes automatizados)
│   ├── README.md                     # Guia de testes, fixtures e análise de cobertura
│   ├── conftest.py                   # Fixtures compartilhadas pytest
│   ├── test_cstr_plant.py            # Testes do modelo de planta e EDOs
│   ├── test_pid_controllers.py       # Testes da classe PIDController e anti-windup
│   ├── test_tuning_methods.py        # Testes de ZN, CC, SIMC e cálculo de Ms
│   ├── test_metrics.py               # Testes de validação das métricas IAE/ITAE/TV
│   ├── test_pareto.py                # Testes de dominância e fronteira de Pareto
│   └── test_plot_styles.py           # Testes de conformidade gráfica IEEE
│
├── papers/                           # 3 manuscritos Elsevier (cas-dc.cls) — fonte canônica
│   ├── 01_journal_of_process_control/          # Artigo 1 (JPC) — tag v1.0.0-jpc-submission
│   ├── 02_computers_chemical_engineering/      # Artigo 2 (CACE)
│   └── 03_chemical_engineering_research_design/ # Artigo 3 (ChERD)
│       # cada pasta: main.tex, sections/, figures/, tables/, ready-to-overleaf/, ready_to_overleaf.zip
│
├── Biblioteca/                       # Acervo bibliográfico de referência e literatura clássica
├── Projeto/                          # Cronograma e documentação de planejamento das fases PROIC
└── scripts/                          # Utilitários de automação e sincronização
    ├── README.md                     # Guia de uso dos scripts
    ├── github/
    │   └── sync_to_github.ps1        # Script PowerShell para sincronização com GitHub API
    └── overleaf/
        ├── overleaf_push.ps1         # Upload automatizado para o Overleaf
        └── overleaf_pull.ps1         # Download de atualizações do Overleaf
```

---

## Guia de Instalação e Execução

### 1. Pré-Requisitos de Ambiente
* Python 3.12 ou superior (testado e validado em Python 3.14).
* Gerenciador de pacotes `pip`.
* Git ou PowerShell com acesso à internet para sincronização.

### 2. Configuração do Ambiente Virtual (`.venv`)

No terminal PowerShell na raiz do repositório:

```powershell
# Criação do ambiente virtual
python -m venv .venv

# Ativação do ambiente virtual
.venv\Scripts\Activate.ps1

# Instalação das dependências em modo de desenvolvimento
pip install -e ".[dev]"
```

### 3. Execução dos Testes Automatizados

Para certificar a integridade de todas as equações e rotinas numéricas:

```powershell
# Execução simples com resumo detalhado
python -m pytest tests/ -v --tb=short

# Execução com relatório de cobertura de código
python -m pytest --cov=src --cov-report=term-missing tests/
```
*Resultado esperado: 56 testes passando com 100% de sucesso.*

---

## Guia de Uso no Spyder 6

O projeto foi inteiramente adaptado com blocos de células compatíveis com a IDE **Spyder 6**, permitindo inspeção interativa, depuração passo a passo e visualização direta no painel de gráficos.

### Passo 1: Abrir o Projeto no Spyder 6
1. Abra o **Spyder 6**.
2. No menu superior, clique em **Projects** $\to$ **Open Project...** e selecione o diretório raiz do repositório:
   `C:\Users\biely\OneDrive\Área de Trabalho\2026.2\IC`
3. Certifique-se de que o interpretador Python ativo no Spyder aponte para o ambiente virtual `.venv` do projeto:
   * **Tools** $\to$ **Preferences** $\to$ **Python Interpreter** $\to$ **Use the following Python interpreter**:
   * Selecione: `C:\Users\biely\OneDrive\Área de Trabalho\2026.2\IC\.venv\Scripts\python.exe`.

### Passo 2: Execução Interativa por Blocos de Células (`# %%`)
Todos os scripts em `experiments/` utilizam demarcadores de célula padrão `# %%`.
1. Abra qualquer script, por exemplo, `experiments/exp_01_classical_benchmark.py`.
2. Posicione o cursor dentro do bloco desejado.
3. Pressione **`Shift + Enter`** para executar a célula atual no console interativo IPython e avançar para a próxima.
4. Para reexecutar apenas a célula atual sem avançar, utilize **`Ctrl + Enter`**.

### Passo 3: Inspeção no Variable Explorer e Plots
* **Variable Explorer (Explorador de Variáveis):** Permite inspecionar diretamente os objetos `CSTRPlant`, os arrays de trajetórias temporais (`t`, `states`, `u_applied`), e as estruturas `ControlPerformanceMetrics`. Dando duplo clique em uma variável, é possível analisar numericamente as trajetórias.
* **Plots (Painel de Gráficos):** As figuras geradas em alta resolução (300 DPI) com estilização IEEE Transactions aparecem automaticamente na aba **Plots** do Spyder, permitindo *zoom*, comparação e exportação interativa.

---

## Sincronização com o GitHub

Para sincronizar o código-fonte, tabelas, gráficos e documentações com o repositório remoto oficial no GitHub ([https://github.com/Marques-svnt/IC-CSTR-Control-Benchmark](https://github.com/Marques-svnt/IC-CSTR-Control-Benchmark)), utilize o script automatizado via REST API:

```powershell
# Execução da sincronização com mensagem de commit explicativa
.\scripts\github\sync_to_github.ps1 -Message "docs: atualizacao completa da documentacao tecnica do Artigo 1"
```

O script detecta automaticamente todos os arquivos modificados ou criados em `src/`, `experiments/`, `tests/`, `papers/` e na raiz, aplicando hash SHA para evitar uploads desnecessários.

---

## Licença e Agradecimentos

Este software e os manuscritos associados são disponibilizados sob a licença [MIT](LICENSE).

O projeto é desenvolvido na **Universidade Estadual de Santa Cruz (UESC)**, no âmbito do Colegiado de Engenharia Química e do Departamento de Ciências Exatas e Tecnológicas (DCET), financiado pelo Programa de Iniciação Científica (PROIC) com apoio da **FAPESB** e do **CNPq** (Edital 34/2026).

Agradecimentos especiais ao orientador **Prof. Dr. Elilton Rodrigues Edwards** pela orientação técnica, revisão científica e direcionamento acadêmico ao longo de todas as fases do projeto.
