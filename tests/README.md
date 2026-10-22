# Suíte de Testes Automatizados e Testes Baseados em Propriedades

> **Documentação de Engenharia da Qualidade de Software e Verificação Numérica**  
> A integridade matemática das equações fenomenológicas, dos controladores em tempo discreto, do integrador RK45 e das métricas de desempenho é garantida por uma suíte de **125 testes automatizados** utilizando os frameworks `pytest` e `hypothesis`.

[![Tests: Pytest](https://img.shields.io/badge/tests-124%20passed%20%7C%201%20xfailed-brightgreen.svg)](https://docs.pytest.org/)

---

## 1. Visão Geral da Suíte de Testes (15 Módulos de Verificação)

| Arquivo de Teste | Qtd. Testes | Escopo e Componentes Validados |
|---|---|---|
| [`test_cstr_plant.py`](test_cstr_plant.py) | 10 | Conservação de massa/energia, cinética de Arrhenius, cálculo de estado estacionário e Jacobiana analítica vs diferenças finitas centrais ($O(h^2)$). |
| [`test_pid_controllers.py`](test_pid_controllers.py) | 7 | Ações P, I, D, anti-windup direcional cobrindo saturação de amplitude $[u_{\min}, u_{\max}]$ e taxa de deslocamento ($S_{\max}$), filtro N e derivada na medição. |
| [`test_classical_control.py`](test_classical_control.py) | 14 | Sintonias clássicas (ZN, CC, TL, AMIGO, SIMC), congelamento do integrador durante rampa limitada por *slew-rate* e cálculo de $M_s$. (1 xfail estrito em TL-PID $M_s \approx 2.32$). |
| [`test_tuning_methods.py`](test_tuning_methods.py) | 6 | Sintonias analíticas para ação reversa ($K_p < 0$), cálculo de pico $H_\infty$ e otimização Nelder-Mead constrita com barreira quadrática. |
| [`test_cascade_controller.py`](test_cascade_controller.py) | 4 | Estrutura em cascata mestre-escravo, propagação de limites físicos e desacoplamento dinâmico. |
| [`test_cascade_and_unstable.py`](test_cascade_and_unstable.py) | 11 | Estabilização no ponto de sela instável com autovalor positivo ($\lambda_1 = +0.744\text{ min}^{-1}$), cinética contínua de incrustação e detecção de $t_{\text{runaway}}$. |
| [`test_nmpc_closed_loop.py`](test_nmpc_closed_loop.py) | 4 | Simulação em malha fechada do controlador NMPC via CasADi/IPOPT sob horizontes finitos. |
| [`test_nmpc_and_neural_control.py`](test_nmpc_and_neural_control.py) | 5 | Verificação de tempo de execução, ausência de falhas no solver e interfaces preditivas. |
| [`test_sobol_and_nmpc.py`](test_sobol_and_nmpc.py) | 5 | Invariância estrita a ruído térmico do NMPC-Oracle, equivalência nominal entre NMPC-MHE e NMPC-Oracle na ausência de ruído, e decomposição de variância de Sobol. |
| [`test_property_invariants.py`](test_property_invariants.py) | 18 | **Testes baseados em propriedades via `hypothesis`:** Não-negatividade das concentrações ($C_A \ge 0$), temperaturas físicas ($T > 0$), dissipação de energia e invariantes de Van Heerden. |
| [`test_metrics.py`](test_metrics.py) | 6 | Exatidão matemática de $\text{IAE}$ contra o estado verdadeiro ($T_{\text{true}}$ sem ruído), $\text{ITAE}$ ajustado ao tempo do degrau ($t - t_{\text{step}}$) e variação total do atuador ($\text{TV}$). |
| [`test_pareto.py`](test_pareto.py) | 26 | Relação de dominância multi-objetivo, filtragem de fronteira com $M_s \le 1.6$, normalização euclidiana e detecção do ponto de joelho (*knee point*). |
| [`test_plot_styles.py`](test_plot_styles.py) | 3 | Conformidade tipográfica com periódicos da Elsevier e IEEE Transactions ($300\text{ DPI}$, famílias vetoriais e paletas acessíveis). |
| [`test_neuro_pid.py`](test_neuro_pid.py) | 4 | Verificação da rede neural adaptativa acoplada aos ganhos PID. |
| [`test_supervisory_graph.py`](test_supervisory_graph.py) | 2 | Grafo de supervisão de segurança e desvio de rota em condições de risco de runaway. |
| **Total Geral** | **125 Testes** | **124 Passed \| 1 Expected XFail (100% de Conformidade)** |

---

## 2. Testes Baseados em Propriedades (`test_property_invariants.py`)

Para além dos testes unitários pontuais, funções matemáticas e rotinas físicas são submetidas a testes de estresse por propriedades via biblioteca **`hypothesis`** (`@given(...)`):

* **Conservação e Não-Negatividade de Estados:** Para quaisquer perturbações aleatórias sorteadas no espaço de parâmetros válidos, o vetor de concentração física satisfaz estritamente $C_A(t) \ge 0$ e a temperatura do reator permanece dentro dos limites de consistência física ($T(t) \ge 100\text{ K}$).
* **Monotonicidade de Atuadores:** A taxa de variação da ação de controle aplicada pelo atuador respeita $|u_k - u_{k-1}| \le S_{\max} \cdot \Delta t$ em todas as transições.
* **Invariantes de Van Heerden:** Verificação de que para vazões de fluido refrigerante $q_j > q_{j,\text{crit}}$, a curva de remoção de calor intersecta a curva de geração de calor em equilíbrios termodinâmicos válidos.

---

## 3. Como Executar a Suíte de Testes

Certifique-se de que o ambiente virtual está ativo:

```bash
# Ativação do ambiente
source .venv/bin/activate

# 1. Execução rápida e silenciosa (resultado padrão)
pytest -q

# 2. Execução detalhada com rastreamento de cada teste
pytest -v --tb=short

# 3. Execução focada nos testes de propriedades matemáticos (Hypothesis)
pytest tests/test_property_invariants.py -v

# 4. Execução com relatório de cobertura de código
pytest --cov=src --cov-report=term-missing tests/
```
