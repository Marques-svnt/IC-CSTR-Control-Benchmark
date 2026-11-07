# IC-T38 — Relatório de execução (Paper 1, JPC)

Data: 2026-11-07 · Executor: Claude Code · Branch: `jpc-v9-t38-litaudit` (a partir de `jpc-v9`, sem merge)
Ticket: `Claude outputs/TICKET_PAPER1_LITAUDIT_ANTIMOCKING.md` (não está em `.antigravity/`; o `TICKETS.md` não lista o IC-T38).

## Status: PARCIAL — parado em T38.4 aguardando decisão do autor sobre o artigo 2.1

`python scripts/jpc_numbers.py` aborta de propósito, antes de escrever qualquer arquivo:

```
ValueError: audit_coding.csv: uses_pid is empty for ['2.1']; the author must code it yes/no before regenerating
```

**Decisão do artigo 2.1 (Algerian Journal of Signals and Systems, "PSO-tuned feedback controllers"): NÃO RESOLVIDA.**
Para liberar: preencher `uses_pid` (yes/no) da linha `2.1` em `papers/01_journal_of_process_control/repository/audit_coding.csv`.
Se `no`, também mudar `loop_sign` de `no` para `not applicable` na linha 2.1 de `audit_coding.csv` **e** na linha 2.1 de `literature_audit.csv`; se `yes`, `loop_sign` fica `no`.
Depois: rodar o gerador, `check_text_numbers.py`, `check_main_supp_consistency.py`, copiar `generated/` e `tables/literature_audit.tex` para `overleaf-pós-revisões/` e compilar.

## Feito

| Tarefa | Estado | Arquivos |
|---|---|---|
| T38.1 dados | feito, exceto 2.1 | `repository/audit_coding.csv` (coluna `uses_pid` após `controller_class`; 1.10, 2.3, 3.25 = yes; 1.3, 1.8, 1.13 e os 5 preditivos = no; 2.1 vazio); `loop_sign` no → not applicable em 1.3, 1.8, 1.13 em `audit_coding.csv` e `literature_audit.csv` (3 linhas, CRLF preservado) |
| T38.2 gerador | feito | `scripts/jpc_numbers.py`: macro `litpid`; erro claro se `uses_pid` vazio em não preditivo; erro se `loop_sign = n.a.` não coincide com não-PID; erro se `litpid` ≠ artigos com ação do laço aplicável; legenda nova (sem dígitos) |
| T38.3 texto | feito | `overleaf-pós-revisões/sections/01_introduction.tex` (linha 3), `overleaf-pós-revisões/supplementary.tex` (linha 286). Nenhum outro `.tex` usa `\vlitloopsign*` além de `generated/numbers.tex` |
| T38.4 regenerar/verificar | **bloqueado** | ver "Prévia hipotética" |
| T38.5 typos | parcial, ver discrepâncias | `overleaf-pós-revisões/tables/antiwindup_deadband.tex`, `experiments/build_paper_assets.py` |

## Discrepâncias entre o ticket e o repositório

1. **T38.5, typo 1 já corrigido:** `02_plant_actuator_limits.tex:69` já tem `(Section~\ref{subsec:limitations})`. Nada a fazer.
2. **T38.5, typo 2 não é ponto duplo:** a legenda tinha `Table S16.}` (um ponto). O problema real era o "S16" fixo. Troquei por `Table~\ref{tab:stiction}` (a tabela está no suplemento, onde `tab:stiction` é S16 por `generated/supprefs.tex`; `\suppref` serve para o texto principal, não para o suplemento). A legenda é gerada por `experiments/build_paper_assets.py:1724`, então corrigi o gerador e o arquivo. Não rodei a campanha do `run_deadband_test`; só a legenda mudou. O `tables/antiwindup_deadband.tex` da pasta-pai continua com a legenda antiga ("Stiction is not modelled") e não foi tocado.
3. `build_paper_assets.py` já tinha uma alteração não commitada na mesma linha (de "Stiction is not modelled." para "...Table S16."). O commit inclui essa alteração do autor junto com a minha (não dá para separar: é a mesma linha).
4. O ticket supõe que `jpc_numbers.py` imprime as tabelas em `overleaf-pós-revisões/`; ele escreve só na pasta-pai (`generated/`, `tables/`). A cópia para `overleaf-pós-revisões/` é manual (T38.4.3). Antes da mudança, `generated/` e `tables/` das duas pastas eram idênticos, exceto a legenda de `literature_audit.tex` editada à mão no lado `pós-revisões`, que a cópia vai sobrescrever.
5. `overleaf-pós-revisões/` é **untracked** no git. As edições T38.3/T38.5 nessa pasta estão no disco mas **não foram commitadas** (adicionar a pasta inteira traria figuras, aux etc.).

## Baseline

Antes de qualquer mudança, `jpc_numbers.py` reproduz byte a byte `generated/`, `tables/` e `results/jpc/v9_numbers.csv` commitados (sem diff).

## Prévia hipotética da regeneração (cópia em scratchpad, nada gravado no repositório)

Só para validar o gerador; **não é decisão sobre o 2.1**. Em ambos os cenários mudam apenas `vlitloopsignna`, `vlitloopsignapp`, o novo `vlitpid`, `tables/literature_audit.tex` e o espelho `results/jpc/v9_numbers.csv`.

| Macro | Hoje | 2.1 = no | 2.1 = yes |
|---|---|---|---|
| `\vlitloopsign` | 0 | 0 | 0 |
| `\vlitloopsignna` | 5 | 9 | 8 |
| `\vlitloopsignapp` | 7 | 3 | 4 |
| `\vlitpid` | (novo) | 3 | 4 |
| `\vlitantiwindupapp` | 7 | 7 | 7 |

Linha "Loop action" da Tabela S36 (yes / no / n.a. / not verifiable): hoje 0 / 7 / 5 / 0; com 2.1 = no, 0 / 3 / 9 / 0; com 2.1 = yes, 0 / 4 / 8 / 0 (o 2.1 manteria `loop_sign = no`).

## Verificações já executadas

- `ruff check scripts/jpc_numbers.py experiments/build_paper_assets.py`: limpo.
- `pytest tests/test_classical_control.py`: 30 passed, 1 xfailed (TL-PID, esperado).
- Gerador: aborta com a mensagem acima, sem alterar `generated/`, `tables/` ou `results/`.

## Pendências e riscos

- `check_text_numbers.py` regenera os macros e **vai falhar enquanto o 2.1 estiver vazio** (herda o erro do gerador); idem qualquer `make` que chame o gerador.
- Compilação de `main.tex`/`supplementary.tex` (T38.4.3) e a varredura de palavras-número (T38.4.4) dependem da regeneração; não feitas.
- A legenda gerada ainda diz "the five predictive controllers" (contagem digitada à mão, como no texto prescrito pelo ticket). Sugestão: usar `\vlitantiwindupna`/gerar a palavra a partir da contagem em outro ticket.
- Suplemento ainda tem contagens por extenso fora do trecho do ticket ("three fixed search strings", "five items", "three rows"); são parâmetros de protocolo, mas entram na varredura do T38.4.4.
