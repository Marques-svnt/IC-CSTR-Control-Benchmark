# IC-T38 — Relatório de execução (Paper 1, JPC)

Data: 2026-11-07 · Executor: Claude Code · Branch: `jpc-v9-t38-litaudit` (a partir de `jpc-v9`, sem merge)
Ticket: `Claude outputs/TICKET_PAPER1_LITAUDIT_ANTIMOCKING.md` (não está em `.antigravity/`; o `TICKETS.md` não lista o IC-T38).

## Status: CONCLUÍDO (T38.1 a T38.5), com pendências listadas no fim

## Decisão do autor sobre o artigo 2.1 (correção da codificação)

A proposta inicial do ticket tratava o 2.1 ("PSO-tuned feedback controllers") como não preditivo e deixou `uses_pid` vazio. O autor leu o texto completo: é **um MPC com parâmetros ajustados por PSO, sem PID**. Correção aplicada (e nada mais):

| Arquivo, linha 2.1 | Campo | Antes | Depois |
|---|---|---|---|
| `audit_coding.csv` | `controller_type` | PSO-tuned feedback controllers | MPC with PSO-tuned parameters |
| `audit_coding.csv` | `controller_class` | non-predictive | predictive |
| `audit_coding.csv` | `uses_pid` | (vazio) | no |
| `audit_coding.csv` | `anti_windup` | no | not applicable |
| `audit_coding.csv` | `loop_sign` | no | not applicable |
| `literature_audit.csv` | `anti_windup` | no | not applicable |
| `literature_audit.csv` | `loop_sign` | no | not applicable |

O campo `note` do 2.1 em `literature_audit.csv` ("PSO-tuned control; ...") não foi alterado, conforme instrução. Consequência: o 2.1 passa a contar entre os preditivos, então os preditivos são 6 (antes 5), não só no `loop_sign` mas também no `anti_windup`.

## Arquivos alterados

Rastreados e commitados:
- `papers/01_journal_of_process_control/repository/audit_coding.csv` — coluna `uses_pid`; `loop_sign` n.a. em 1.3, 1.8, 1.13 e 2.1; correção do 2.1.
- `papers/01_journal_of_process_control/repository/literature_audit.csv` — `loop_sign` n.a. em 1.3, 1.8, 1.13 e 2.1; `anti_windup` n.a. no 2.1 (CRLF preservado).
- `scripts/jpc_numbers.py` — macro `litpid`; erro claro se `uses_pid` vazio; checagens cruzadas `loop_sign`/`uses_pid`/`litpid`; legenda sem número fixo ("the purely predictive controllers").
- `experiments/build_paper_assets.py` — legenda do `antiwindup_deadband` usa `\ref{tab:stiction}` (inclui uma alteração do autor já pendente na mesma linha).
- `papers/01_journal_of_process_control/generated/numbers.tex`, `tables/literature_audit.tex`, `results/jpc/v9_numbers.csv` — regenerados.
- `.antigravity/T38_REPORT.md` — este relatório.

Não rastreados (a pasta `overleaf-pós-revisões/` é untracked; editados no disco, **não commitados**):
- `overleaf-pós-revisões/sections/01_introduction.tex` (linha 3), `supplementary.tex` (linha 286), `tables/antiwindup_deadband.tex` (legenda), e cópias de `generated/numbers.tex` e `tables/literature_audit.tex`.

## Números (antes → depois)

| Macro | Antes | Depois |
|---|---|---|
| `\vlitantiwindup` | 2 | 2 |
| `\vlitantiwindupna` | 5 | 6 |
| `\vlitantiwindupapp` | 7 | 6 |
| `\vlitloopsign` | 0 | 0 |
| `\vlitloopsignna` | 5 | 9 |
| `\vlitloopsignapp` | 7 | 3 |
| `\vlitpid` | (não existia) | 3 |

Tabela S36 (yes / no / n.a. / not verifiable): "Anti-windup logic declared" 2 / 5 / 5 / 0 → 2 / 4 / 6 / 0; "Loop action stated" 0 / 7 / 5 / 0 → **0 / 3 / 9 / 0**.

## Diff antes/depois (regeneração real)

Comparado com o snapshot de `generated/` e `tables/` tirado antes de qualquer mudança (o gerador reproduzia esse snapshot byte a byte):
- Arquivos que mudaram: `generated/numbers.tex`, `tables/literature_audit.tex`, `results/jpc/v9_numbers.csv` (espelho de proveniência). Nenhuma outra tabela mudou; `generated/supprefs.tex` não mudou.
- `numbers.tex`: só `vlitantiwindupna`, `vlitantiwindupapp`, `vlitloopsignna`, `vlitloopsignapp` e o novo `vlitpid`.
- `literature_audit.tex`: a legenda e as duas linhas da tabela acima.

**Atenção:** a instrução inicial dizia que só `vlitloopsign*`, `vlitpid` e `literature_audit.tex` poderiam mudar. `vlitantiwindupna` e `vlitantiwindupapp` também mudaram, mas isso é consequência direta da correção do 2.1 (`anti_windup` n.a.) e o valor `vlitantiwindupapp` = 6 é o esperado pelo autor. Nenhuma outra macro mudou.

## Verificações executadas

- `jpc_numbers.py`: 400 macros (399 + `litpid`), 4 tabelas, sem erro.
- `check_text_numbers.py`: sai com 0; "generated/numbers.tex reproduces from the CSV mirrors". Aviso pré-existente e sem relação: no suplemento, o decimal `0.525` não está em nenhum CSV.
- `check_main_supp_consistency.py`: todas as linhas `ok`, sai com 0.
- `ruff check .`: limpo. `pytest`: 168 passed, 1 xfailed (TL-PID, esperado).
- Compilação em `overleaf-pós-revisões/` com `latexmk -pdf`: `supplementary.pdf` 26 páginas, `main.pdf` 14 páginas; 0 erros, 0 referências/citações indefinidas, 0 `??` no texto. Um overfull de 123,6 pt em `main`, já documentado no IC-T14 (caixa de keywords do `cas-dc`).
- PDF: a Tabela S36 mostra "Loop action stated 0 / 3 / 9 / 0"; a introdução lê "of the 6 whose control law is not purely predictive, 2 the anti-windup logic. ... 3 of these 6 use PID, and 0 of them state it."; o suplemento (S8) lê "...coded not applicable for the 6 articles ... counted over the 6 others ... counted over the 3 articles that use PID"; a legenda do `antiwindup_deadband` mostra "Table S16".
- T38.4.4, palavras-número em `01_introduction.tex` e `supplementary.tex`: nenhuma ocorrência nas passagens da auditoria refere-se a contagens da auditoria. Restam parâmetros de protocolo na linha 286 do suplemento ("three fixed search strings", "five items coded", "three rows of Table S36"); não são contagens da auditoria e não foram alterados.

## Discrepâncias entre o ticket e o repositório

1. **T38.5, typo 1:** `02_plant_actuator_limits.tex:69` já tinha `(Section~\ref{subsec:limitations})`. Nada a fazer.
2. **T38.5, typo 2:** a legenda tinha `Table S16.}` (um ponto, não dois). O problema real era o "S16" fixo; foi trocado por `\ref{tab:stiction}` (a tabela está no suplemento, onde `tab:stiction` é S16). Corrigido no gerador e no arquivo. A campanha do `run_deadband_test` não foi rodada; só a legenda mudou.
3. O `jpc_numbers.py` escreve só na pasta-pai; a cópia para `overleaf-pós-revisões/` foi feita à mão (T38.4.3). A única tabela que difere entre as duas pastas é `tables/antiwindup_deadband.tex` (a da pasta-pai ainda tem a legenda antiga "Stiction is not modelled" e não foi tocada).

## Pendências e riscos

- **Autor:** decidir se `overleaf-pós-revisões/` (untracked) entra no git; hoje as edições dela estão só no disco.
- **Autor:** a linha 286 do suplemento diz "five items coded", mas a Tabela S36 lista 7 itens. Não é contagem da auditoria e não foi alterada; vale conferir.
- O CSV `audit_coding.csv` continua com `second_coder` vazio (segunda codificação independente não feita).
- `tables/antiwindup_deadband.tex` da pasta-pai e `ready_to_overleaf.zip` não foram regenerados.
