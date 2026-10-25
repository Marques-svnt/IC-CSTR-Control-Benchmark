# CHANGELOG — Artigo 1 (JPC), v5 → v6

Referência: `papers/review/parecer_r5.md` (5ª rodada, nota 73). "Obr." = exigência obrigatória, "Rec." = recomendada, com o número do parecer. Valores "antes" vêm da v5 (`cut/v5/`); valores "depois" vêm de `generated/numbers.tex`, gerado por `scripts/jpc_v6_numbers.py` a partir de `results/jpc/*.csv`.

## Fase 1 — reenquadramento e corte (branch `phase1/jpc-reframe-cut`)

| Exigência | O que mudou | Arquivos | Antes → depois |
|---|---|---|---|
| Obr. 1 (escopo) | Título, resumo, highlights, palavras-chave, Introdução e conclusões reescritos em torno de anti-windup e restrições de atuador. A Introdução declara que o artigo não é estudo de sintonia PID: os ganhos são fixos e servem de banco de provas. Seção 3 renomeada para "PID implementation and anti-windup logic"; "Tuning rules" vira "Test-bed gains" | `main.tex`, `highlights.tex`, `sections/01`, `03`, `05` | Título "Anti-Windup for Reverse-Acting PID Loops under…" → "Anti-Windup under Amplitude and Slew-Rate Limits in Reverse-Acting Process Loops…" |
| Obr. 1 (escopo) | Conteúdo de sintonia pura movido para o material suplementar: ITAE sob limite de Ms e seu custo, erro de modelo do ótimo, fora da amostra, 2-DOF, Ms/margens FOPTD × planta, locus de Pareto/SIMC, estudo de N, campanha de ruído completa, carga replicada, Sobol e Shapley. O texto movido foi preservado verbatim; nada foi apagado | `supplementary.tex` (novo), `cut/v5/` (cópia integral da v5) | Seções S1–S6 do suplementar |
| Obr. 2 (extensão) | Corte e condensação: as Tabelas 3 + 14 da v5 viram uma tabela de banco de provas; o mapa de regime, a zona morta e o 2º ponto de operação viram tabelas condensadas | `tables/v6_*.tex` (gerados) | 25 → 12 páginas (incluindo a página de highlights); 28 tabelas + 9 figuras → 9 tabelas + 4 figuras + 1 algoritmo; `texcount` ≈ 4.300 palavras de texto + 13 floats × 150 ≈ 6.300 (nominal do guia: 7.500) |
| Obr. 2 (regra 2 do roteiro) | Todo número do texto principal, do resumo e das conclusões é macro gerada dos CSV; o script registra macro, valor e fonte | `scripts/jpc_v6_numbers.py`, `generated/numbers.tex`, `results/jpc/v6_numbers.csv` | 149 macros |
| Obr. 5 (carta) | Rascunho do parágrafo de escopo e do parágrafo sobre os artigos companheiros | `cover_letter.md` | Títulos dos companheiros a confirmar pelo autor |
| Rec. 1 (parcial) | O resumo e a conclusão 3 passam a citar o critério Tt^cv (escolha no degrau de projeto, julgada em ±5 K) | `main.tex`, `sections/05` | "within 2% (minimax)" → "within 2% on larger steps (Tt^cv)"; o resto da Rec. 1 fica para a Fase 2 |
| Rec. 7 | O highlight 4 da v5 ("Exact-loop Ms bound gives 11% ITAE…") saiu junto com o conteúdo de sintonia | `highlights.tex` | Item removido; os cinco highlights novos têm 66–83 caracteres |

### Correções encontradas durante o corte (regra 6: muda a afirmação, não o resultado)

| Local | Problema | Antes → depois |
|---|---|---|
| Prop. 1, parágrafo seguinte (§3.2) | I* estava errado no texto | "I* ≈ 300 L/min" → I* = 945 (ZN) e 1050 (CC) L/min, calculados pelo script a partir do modelo e dos ganhos |
| Resumo e conclusão 1 | IAE com três casas, que não existem no CSV da ablação | 0,940 → 104,123 → 0,94 → 104,12 (`antiwindup_ablation.csv`) |
| Resumo | "o erro se fixa em −16,7 K" tinha sinal ambíguo (e = T_sp − T é positivo) | → "a temperatura fica 16,72 K abaixo do setpoint" |
| Suplementar S4 (estudo de N) | Na 3ª rodada as sementes do estudo de N foram alinhadas às da campanha de ruído, mas o texto não foi atualizado | TV em σ = 0,01: 581→523 (ZN), 578→537 (CC) → 585→529, 583→543; faixa em σ = 0,05: 726–744 → 731–749 (as porcentagens de 10% e 7% não mudam) |
| Tabela 1 (v5) | Tabela de uma coluna invadia a coluna da direita (overfull de 112 pt) | → `table*` de largura total |
| Eqs. da prova da Prop. 1 e do retrocálculo (v5) | Overfull de 67 e 78 pt | Prova em duas linhas (`align*`); T_t padrão fora da equação |
| Eq. de u_req (v5) | Overfull de 187 pt | Movida para S1 do suplementar |
| Legenda da Tabela de ablação | Remetia à tabela de benchmark, que foi para o suplementar | → remete à tabela de banco de provas (`experiments/build_paper_assets.py`; CSV idêntico) |
