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

## Fase 2 — ajustes recomendados que dependem de código (branch `phase2/backcalc-tt`)

| Exigência | O que mudou | Arquivos | Antes → depois |
|---|---|---|---|
| Rec. 1 (Tt^cv principal) | T_t^cv passa a ser o critério principal no resumo, no highlight 3, na §4.4 e na conclusão 3; T_t^mm fica como confirmação in-sample | `main.tex`, `highlights.tex`, `sections/04`, `05` | Highlight 3: "…one Tt per loop (minimax) is within 2%…" → "Back-calculation with Tt chosen on the design step matches directional clamping" (79 caracteres) |
| Rec. 1 (curva fora de [Td, Ti]) | A escolha no degrau de projeto foi refeita sem a restrição de faixa. ZN, CC e SIMC têm o mínimo na borda da faixa; sem a restrição ele sai dela (ZN e CC em Δt = 0,020 min; SIMC em 10 T_i = 6,427 min, borda da varredura) e a pior razão em ±5 K não melhora em nenhum laço (maior queda 0,00; maior subida 0,08, SIMC) | `experiments/build_paper_assets.py` (`run_tt_curve`), `tables/antiwindup_tt_summary.tex` | Tabela com cabeçalhos curtos e três colunas novas (free T_t^cv, in range, free: ±5 K) |
| Rec. 1 (TV e overshoot) | Nova tabela compara retrocálculo com T_t^cv e regra direcional em IAE, TV e M_p nos três degraus. Para ZN e CC o retrocálculo tem menor TV e menor overshoot em 5 de 6 casos (CC em +5 K: TV 241,9 → 101,2 L/min, M_p 40,8% → 11,3%); para o SIMC move mais a válvula (+20 a +38%) | `tables/antiwindup_tt_tvmp.tex`, `results/jpc/antiwindup_tt_tvmp.csv` | Nova Tabela 7 no texto principal |
| Rec. 2 (erro de modelo com perturbações físicas) | **Não rodado:** o teste de erro de modelo foi para o suplementar S2 junto com o ótimo de malha exata; a frase da conclusão 3 que pedia qualificação saiu do texto principal | — | A hipótese do parecer (Ms_lin máx. 1,30 do ótimo exato nos seis cantos físicos) segue não verificada com o código dos autores |
| Rec. 3 (IC dos Shapley) | **Não rodado:** Sobol e Shapley estão só no suplementar S6; o parecer diz que o corte elimina a exigência | — | — |
| Regra 1 (divergência > 2%) | Nenhum valor já publicado mudou: `antiwindup_tt_sweep.csv` idêntico, colunas antigas da tabela-resumo idênticas | — | Sem divergência |

Extensão após a Fase 2: 13 páginas (incluindo a de highlights).

## Fase 3 — conformidade (branch `phase3/conformity`)

| Exigência | O que mudou | Arquivos | Antes → depois |
|---|---|---|---|
| Formato (guia/template) | Classe atualizada para a versão oficial do zip enviado (cas-dc 2.4, 2024-05-04); duas colunas, declarações (IA generativa, CRediT, conflito de interesse), dados e 6 palavras-chave conferidos. Estilo de referências mantido em `elsarticle-num` (numérico, ordem de citação), que é o que o guia pede; o template traz como padrão um estilo autor-ano | `cas-dc.cls`, `cas-common.sty` | 2.3 (2021) → 2.4 (2024) |
| Obr. 4 (ordem das referências) | Script que confere a numeração pela ordem de primeira citação (lida do `.aux`, em ordem de página) e a existência de cada chave. A desordem apontada no parecer ([31]–[35] antes de [23]–[30]) era artefato da extração de texto em duas colunas: na v5 a ordem já estava correta, e na v6 também | `scripts/check_citation_order.py` | Principal: 31 referências em ordem; suplementar: 11 em ordem |
| Obr. 4 (abreviação de periódicos) | Nomes de periódicos abreviados conforme a LTWA (ex.: J. Process Control, Chem. Eng. Sci., IEEE Control Syst. Mag., Ind. Eng. Chem. Res.) | `references.bib` | 25 campos `journal` abreviados |
| Obr. 4 (verificação [18]–[22] e [29]–[33] da v5) | Conferidas no Crossref (DOI, título, 1º autor, ano, volume, primeira página): lerch2021antiwindup, wang2020rate, aksland2022gradient, serrano2024neuron, morohoshi2025nonlinear, garpinger2015software, sato2019optimal, segovia2013noise, alcantara2013pid e marques2020applications sem divergência. Na v6, garpinger2015software, sato2019optimal, alcantara2013pid e marques2020applications deixaram de ser citadas (estavam nas contribuições de sintonia) | `scripts/verify_bib_crossref.py` | Único aviso do script: subtítulo do livro de Hippe (título curto no Crossref) |
| Obr. 3 (dados e software) | Referência de software no formato do guia (criadores, título, Zenodo, data, versão, DOI) com DOI placeholder, citada na seção de dados; README com a receita de reprodução da v6; `CITATION.cff` e `.zenodo.json` com versão, data e DOI placeholder. **Depósito não criado** (aguarda aprovação) | `references.bib`, `main.tex`, `README.md`, `CITATION.cff`, `.zenodo.json` | DOI: `10.5281/zenodo.XXXXXXX` (placeholder) |
