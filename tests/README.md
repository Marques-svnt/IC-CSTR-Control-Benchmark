# Suíte de Testes Automatizados e Cobertura de Código — Artigo 1

> **Documentação de Engenharia da Qualidade de Software e Verificação Numérica**  
> Todos os componentes matemáticos, controladores, algoritmos de otimização e rotinas de pós-processamento são validados por uma suíte abrangente de 56 testes automatizados utilizando o framework `pytest`.

---

## Visão Geral da Suíte de Testes

| Arquivo de Teste | Quantidade de Testes | Componentes Validados |
|---|---|---|
| [`test_cstr_plant.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/tests/test_cstr_plant.py) | 10 | Conservação de massa/energia, cinética de Arrhenius, ponto de equilíbrio e Jacobiana analítica vs diferenças finitas |
| [`test_pid_controllers.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/tests/test_pid_controllers.py) | 7 | Ações P, I, D, anti-windup (Clamping e Back-Calculation), filtro N e derivada na medição |
| [`test_tuning_methods.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/tests/test_tuning_methods.py) | 6 | Sintonias analíticas (ZN, CC, SIMC), cálculo do pico de sensibilidade $M_s$ e otimização ITAE |
| [`test_metrics.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/tests/test_metrics.py) | 4 | Exatidão matemática de IAE, ITAE, ISE, TV, tempo de acomodação ($t_s$) e sobressinal ($M_p$) |
| [`test_pareto.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/tests/test_pareto.py) | 26 | Relação de dominância de Pareto, filtragem da fronteira com restrição $M_s \le 1.6$, normalização e ponto de joelho |
| [`test_plot_styles.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/tests/test_plot_styles.py) | 3 | Dimensões IEEE (coluna simples e dupla), tipografia vetorial e paleta de alto contraste |
| **Total Geral** | **56 Testes** | **100% de Sucesso** |

---

## Fixtures Compartilhadas (`conftest.py`)

O arquivo [`conftest.py`](file:///C:/Users/biely/OneDrive/Área%20de%20Trabalho/2026.2/IC/tests/conftest.py) centraliza as configurações reutilizáveis e objetos fundamentais:

* **`nominal_plant`:** Instância inicializada da classe `CSTRPlant` com parâmetros nominais.
* **`nominal_steady_state`:** Estado de equilíbrio exato calculado numericamente para $\bar{q}_j = 100.0\text{ L/min}$.
* **`foptd_model`:** Modelo First-Order Plus Time Delay calibrado ($K_p = -0.135$, $\tau = 0.380$, $\theta = 0.095$).
* **`actuator_limits`:** Limites físicos operacionais ($u_{\min} = 0$, $u_{\max} = 300\text{ L/min}$, $\text{slew} = 100\text{ L/min}^2$).

---

## Detalhamento dos Módulos de Teste

### 1. `test_cstr_plant.py` — Validação Física do Reator
* **Não-negatividade da Cinética:** Garante que a taxa de reação $r_A(C_A, T) \ge 0$ para qualquer faixa de concentração e temperatura, mesmo sob perturbações térmicas extremas.
* **Convergência do Ponto de Equilíbrio:** Verifica que `find_steady_state` retorna um vetor de estados onde os resíduos das derivadas são estritamente nulos ($\|\dot{x}\| < 10^{-6}$).
* **Jacobiana Analítica vs Diferenças Finitas:** Compara os elementos das matrizes Jacobiana contínua $A = \partial f/\partial x$ e $B = \partial f/\partial u$ calculados analiticamente contra aproximações de diferenças finitas centrais de segunda ordem ($O(h^2)$ com $h = 10^{-6}$), garantindo erro relativo inferior a $10^{-4}$.
* **Injeção Dinâmica de Perturbações:** Valida a resposta das derivadas quando $T_f$ ou $C_{Af}$ são perturbados em tempo real.

### 2. `test_pid_controllers.py` — Algoritmo de Controle Industrial
* **Desacoplamento Proporcional, Integral e Derivativo:** Valida a resposta individual de cada termo em relação a funções erro conhecidas.
* **Eliminação do Choque Derivativo (*Derivative Kick*):** Confirma que quando `derivative_on_measurement=True`, um degrau puro no setpoint não provoca pulsos infinitos na ação de controle.
* **Eficácia dos Métodos Anti-Windup:**
  * No modo `CLAMPING`, a ação integral é imediatamente congelada durante a saturação da válvula se o erro persistir, evitando sobressinais catastróficos no retorno à faixa linear.
  * No modo `BACK_CALCULATION`, a ação integral é corrigida dinamicamente pela diferença $(u_{\text{applied}} - u_{\text{unconstrained}})$.

### 3. `test_tuning_methods.py` — Algoritmos de Sintonia e Robustez
* **Sintonias Analíticas:** Verifica as fórmulas de Ziegler-Nichols, Cohen-Coon e Skogestad SIMC para plantas com ganho estático negativo ($K_p < 0$), certificando que os ganhos proporcionais calculados preservam o sinal correto para ação reversa.
* **Cálculo da Sensibilidade Máxima ($M_s$):** Confirma que a função `calculate_maximum_sensitivity` calcula corretamente a norma $H_\infty$ da sensibilidade de malha fechada sobre uma malha contínua de frequências.
* **Otimização ITAE Constrita:** Assegura que a rotina `tune_by_optimization` converge para ganhos factíveis que respeitam a restrição $M_s \le 1.6$.

### 4. `test_metrics.py` — Precisão das Métricas
* **Quadratura Numérica:** Compara o cálculo trapezoidal de IAE e ITAE com integrais analíticas exatas de funções de teste exponenciais e degrau.
* **Variação Total (TV):** Valida a soma de degraus discretos no atuador.
* **Tempo de Acomodação e Sobressinal:** Verifica a detecção correta da faixa de acomodação de $\pm 2\%$ e a identificação do pico percentual máximo.

### 5. `test_pareto.py` — Análise de Dominância Multi-Objetivo
* **Detecção de Dominância:** Testa casos limites onde um ponto é estritamente melhor, equivalente ou dominado em $(\text{IAE}, \text{TV})$.
* **Filtro de Robustez:** Garante que soluções com $M_s > 1.6$ sejam descartadas antes da avaliação de não-dominância.
* **Knee Point:** Valida que o ponto de joelho selecionado corresponde exatamente ao de menor distância geométrica ao ponto utópico normalizado.

### 6. `test_plot_styles.py` — Padrão Gráfico Editorial
* Certifica a configuração de `matplotlib.rcParams` para impressão e publicação IEEE, incluindo resolução mínima de 300 DPI, famílias tipográficas serifadas e dimensões físicas das figuras.

---

## Como Executar os Testes

### Execução via Terminal (PowerShell)

```powershell
# Ativar o ambiente virtual
.venv\Scripts\Activate.ps1

# 1. Executar todos os 56 testes em modo detalhado
python -m pytest tests/ -v --tb=short

# 2. Executar um arquivo de teste específico
python -m pytest tests/test_cstr_plant.py -v

# 3. Executar com relatório de cobertura de código
python -m pytest --cov=src --cov-report=term-missing tests/
```

### Execução no Spyder 6

1. Abra o arquivo de teste desejado no editor do Spyder 6 (ex.: `tests/test_cstr_plant.py`).
2. No console IPython do Spyder, execute:
   ```python
   !pytest tests/ -v
   ```
3. Alternativamente, para inspecionar um teste interativamente, selecione o bloco do teste e tecle **`F9`** (executar seleção).
