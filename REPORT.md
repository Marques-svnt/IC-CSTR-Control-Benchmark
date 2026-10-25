# REPORT — Artigo 1 (JPC), v7

Branch `jpc-v7`, criado a partir de `phase4/verification` (43aba62). Sem push e sem tag.

## 1. Tarefas

| Tarefa | Estado | Commit | Observação |
|---|---|---|---|
| T1 Regra direcional e SIMC | feito | 0a1f18a, e5681a2 | Recomendação condicionada a ρ ≥ 1. ρ é a demanda de taxa do laço sem limite de slew dividida por S_max·Δt; é ex-ante (não usa IAE). ρ **não separa** SIMC dos demais (AMIGO a 320 L/min² ganha com ρ = 0,21); vale só como condição suficiente nesta planta. Legendas das Tabelas 8/S10 corrigidas. |
| T2 Tt^cv na fronteira | feito | 285bc05 | ZN e CC na borda inferior (T_d), SIMC na superior (T_i). Mínimo livre: Δt para ZN/CC, 10·T_i (topo da grade) para SIMC. |
| T3 Coluna BC(Tt^cv) | feito | 44980a7 | Coluna nas Tabelas 4, 5, 9, S12 e S13. No 2º ponto de operação, Tt^cv foi re-escolhido pelo mesmo critério. |
| T4 "5 de 6 casos" | feito | 89eb942, e5681a2 | Restrito a ZN e CC. TL, SIMC e ITAE ótimo: mais viagem em 6 de 9 casos e overshoot nunca menor. |
| T5 Proposição 1 | feito | 17acf29, e5681a2 | Índices discretos; (H3) mantida como hipótese, mas deduzida de (H2) e da Eq. (10). Hipóteses verificadas em `results/jpc/latch_check.csv`. I⋆ = 945/1050 e T(t_f)−T_sp = −16,72 K conferidos por script. Rodapé sobre a condição extra do código. |
| T6 Zona morta | feito | 5ef4996 | O código corresponde ao texto (o anti-windup vê o comando u_act, não a posição); não foi preciso parar. Equação S (backlash), na ordem sat → taxa → folga. |
| T7 Laço algébrico | feito | 74320d1, e5681a2 | Variante preditor-corretor implementada e testada. Tabela 4 (−2 K): |ΔIAE| ≤ 1,4 %. Em +5 K: ZN −5,9 %, CC −7,1 % (não desprezível; destacado na Seção 3.2). Conclusões inalteradas. |
| T8 Euler explícito | feito | 74320d1 | Tt > Δt/2 e a sobrecorreção são artefatos de Euler explícito. Rodado Tt = 0,1·√(TiTd) com o fator exato (Tabela S): ZN 18,56 → 0,87; CC 18,56 → 0,82. |
| T9 Referências | feito, com ressalva | e1a4f70 | Ver seção 3. |
| T10 Consistência | feito | 7c6701d, bba8010 | (a) todo "Supplementary" do texto principal cita item exato via `\suppref`, exceto o data statement (fora de escopo). (b) sem divergências; ver seção 2. (c) nota na S13. (d) Shapley com 30 sementes. (e) S2 reduzido; o resto foi para `papers/01_journal_of_process_control/repository/S2_tuning_extended.tex`. |
| T11 Tipografia | feito | 285bc05, 44980a7, 7be61de | (a) "ZN, CC and SIMC" fora do modo matemático. (b) legendas 4, 5, 9 com T_t e S_max. (c) unidades (L/min)/K na Tabela 3. (d) eixos conferidos; só o rótulo de eixo cortado da Fig. 2 foi corrigido. |
| T12 Contexto industrial | feito | 1d225b6 | Cita só Shinskey e Åström–Hägglund, já presentes. Sem número de cláusula. |
| T13 Carta | feito | d45ef09 | `cover_letter_v7.md`, 529 palavras. |

T7 e T8 estão num único commit porque mexem nos mesmos arquivos de forma entrelaçada (controlador, teste, S3). O commit do T11 também carrega o laço de 30 sementes do Shapley (T10d) em `build_paper_assets.py`.

## 2. Divergências entre texto principal e Suplementar

`scripts/check_main_supp_consistency.py` compara 13 itens: piores razões de Tt^mm, √(TiTd) e Ti; Tabela 3 contra S1/S3 para os seis laços; Khf contra S3; sign-blind contra none; I⋆; offset do latch. **Nenhuma divergência.** `scripts/check_text_numbers.py`: os números do Suplementar estão nos CSV, exceto 3 constantes (0,525; 36,4; 396,65).

Divergências entre o pedido e os CSV (prevaleceu o CSV):
- T4: overshoot do ITAE ótimo em +5 K é 12,5 % (BC) contra 8,7 % (dir.), não 12,6/8,6.
- T1: razão do SIMC em S_max = 80 é 0,85 em precisão total (0,845 só com os valores arredondados da tabela).
- T1 (Suplementar v6): "for SIMC the trigger never helps" estava errado; em 20 L/min² a razão é 1,05. Corrigido.
- T2: o SIMC com Tt = Ti não "empata" com não ter anti-windup: é 6 % pior em −2 K, igual em −5 K e 12 % melhor em +5 K. O texto dá os números.
- T3: com a coluna Tt^cv, "within 10 % of the best back-calculation" (S3, zona morta) deixou de valer; a regra de taxa fica até 19 % pior que BC(Tt^cv). Texto corrigido.
- T10(d): as médias do Shapley mudaram um pouco em relação à rodada única da v6 (ex.: E_a/R do ZN em IAE 0,09 → 0,13; faixa de C_Af 0,43–0,59 → 0,43–0,61).

## 3. Referências

- [19] **Corrigida, mas confira antes de submeter.** O registro Crossref do DOI 10.1016/j.ifacol.2024.08.093 (e o OpenAlex, que o copia) separa errado os nomes: "Inés Tejado Blas" e "M. Vinagre". Esses dois "autores" só existem nesse trabalho, enquanto Inés Tejado (ORCID 0000-0001-5542-348X) e Blas M. Vinagre (ORCID 0000-0001-5039-0738), ambos da Universidad de Extremadura, têm centenas de trabalhos. A ScienceDirect bloqueou o acesso automatizado, então **não conferi no PDF nem na página do editor**. Como o Crossref está errado, o erro pode voltar via gerenciador de referências.
- [16] Lerch et al., ICSTCC 2021, pp. 413–418: confirmada no Crossref.
- [18] Aksland et al., ACC 2022, pp. 1588–1594: confirmada.
- [20] Morohoshi e Deng, Processes 13(5) 1266, 2025: confirmada.
- [2] Hippe 2006: o DOI já existia; ISBN 978-1-84628-322-2 acrescentado ao `.bib`. O estilo `elsarticle-num` não imprime ISBN.
- Nenhuma referência ficou como "não confirmada".

## 4. Decisões em pontos ambíguos

1. **Nome do script.** Mantive `scripts/jpc_v6_numbers.py`, porque renomear exigiria editar o data statement (regra 2). As tabelas condensadas passaram a `v7_*.tex`, e a lista de macros a `results/jpc/v7_numbers.csv`; `v6_numbers.csv` ficou como base do diff. Resolver quando o data statement entrar no escopo.
2. **Referências ao Suplementar.** Usei `\suppref{label}`, gerado de `supplementary.aux` por `scripts/jpc_supp_refs.py`. Um rótulo inexistente interrompe a compilação. Ordem de build: supp → `jpc_supp_refs.py` → main.
3. **T1, critério.** Nenhuma métrica de demanda testada separa o SIMC: pico de demanda, tempo em limite de taxa, discrepância integrada, overshoot sem gatilho. Reportei a regra unilateral ρ ≥ 1 e disse que ela não separa.
4. **T10(d).** Usei 30 sementes da floresta e da partição de CV, em vez de bootstrap, que vaza duplicatas entre folds. O intervalo mede a estabilidade do estimador, não a incerteza amostral do Sobol; legenda e texto dizem isso.
5. **T10(e).** Mantive no S2 a definição dos pesos 2-DOF, porque a Fig. 1 e a Tabela S1 mostram essas variantes, e o teste de erro de modelo (Tabela S5), que é sobre M_s no FOPTD contra a planta exata. Saíram para o repositório: otimização conjunta dos pesos, ITAE fora da amostra e o locus SIMC com a figura e a tabela.
6. **T6.** A equação completa ficou no Suplementar (Eq. S), e o texto principal ganhou uma frase com a referência; não havia espaço.
7. **Espaço.** Para caber em 12 páginas, não cortei conteúdo. Tirei duplicações (números do SIMC já presentes na Seção 4.6 e na Tabela 9; exemplo do TL já na Tabela 7) e passei a Tabela 10 para uma coluna. O detalhe novo de T6, T7 e T8 está no Suplementar, com referência exata.
8. **Fora do pedido, mas consequência do T1** (feito após o parecer do usuário): resumo e highlight 2 agora qualificam o gatilho de taxa ("restores fast loops; it worsens SIMC").

## 5. Verificação final

1. **PDF** (template `cas-dc` 2.4, Elsevier):
   - Texto principal com **12 páginas** de duas colunas ("Page 12 of 12"); o PDF tem 13 páginas por causa da página de highlights que o template insere.
   - Resumo com 236 palavras pela minha contagem, que expande as macros (a sua contagem da v6 era 227).
   - Highlights: 5 itens com 83, 77, 66, 79 e 71 caracteres, em `highlights.tex`.
   - 6 palavras-chave.
   - Referências em ordem de primeira citação (`check_citation_order.py`: 31 refs, ordem 1–31), com DOI quando há.
   - Nenhuma referência indefinida em main e Suplementar; todo `\suppref` resolve.
   - Desk-check Elsevier passou.
   - Restam 4 caixas estouradas que já existiam na v6 (página de highlights, 1ª linha da introdução e duas de menos de 4 pt); não mexi nelas.
   - Suplementar com 21 páginas.
2. **Rerun do zero** (`build_paper_assets.py jpc-remediation`, 1398 s, depois `jpc_v6_numbers.py`):
   - Todos os CSV de `results/jpc/` reproduzem exatamente os commitados. A única diferença, em `sobol_shapley`, é a formatação "−0.00" → "0.00".
   - Os PNG das figuras são idênticos; os PDF das figuras mudam só nos metadados (mesmo tamanho; não foram commitados de novo).
   - Todas as sementes são fixas: Sobol 2026, RBD-FAST 2026, ruído 100+k e 300+k, Shapley 0–29.
   - `check_text_numbers.py` confirma que `generated/numbers.tex` reproduz a partir dos CSV.
   - As tabelas do PDF são os arquivos `.tex` gerados, incluídos por `\input`.
3. **Diff de números v6 × v7** (`results/jpc/v6_numbers.csv` contra `v7_numbers.csv`):
   - Nenhuma das 161 macros da v6 mudou de valor nem foi removida.
   - 98 macros novas, todas de T1 (ρ e SIMC), T2 (bordas), T3 (BC Tt^cv), T4 (TL, SIMC, ITAE), T5 (latch_check), T7/T8 (preditor-corretor e fator exato) e T10(d) (Shapley).
   - Fora das macros, o único número de tabela que mudou foi o Shapley (S22), por causa das 30 sementes (T10d).
4. **Grep** por "S1 a S5", "TODO", "XXX" e "placeholder":
   - Só o placeholder do Zenodo, em `references.bib` e no data statement, ambos fora de escopo.
   - "Supplementary" sem item: só a frase do data statement ("The tuning-specific analyses are in the Supplementary Material."), mantida pela regra 2.
5. **Testes:**
   - `pytest`: 157 passed, 1 xfailed (xfail pré-existente do TL).
   - `ruff check .` limpo.
   - Testes novos: `preview` da válvula, congelamento no instante k e propriedade (hypothesis) de que o retrocálculo exato nunca sobrecorrige.

## 6. Riscos e pendências para o autor

- [19]: conferir os autores no PDF ou na página do editor (seção 3).
- O nome `jpc_v6_numbers.py` num manuscrito v7 vai parecer inconsistente; resolver junto com o data statement.
- ρ precisa de uma simulação do laço sem o limite de slew. É ex-ante, mas depende do modelo, e a regra ρ ≥ 1 foi verificada em um único reator.
- O intervalo do Shapley não é incerteza amostral; com uma única amostra Sobol, essa incerteza não foi estimada.
- Build do LaTeX: o `\suppref` exige compilar o Suplementar e rodar `scripts/jpc_supp_refs.py` antes da compilação final do main. O pacote `ready-to-overleaf/` **não** foi atualizado para a v7.

## 7. Rodada editorial (revisão maior, 62–77)

| Item | Estado | O que foi feito |
|---|---|---|
| 1 ρ | feito | ρ calculado fora da amostra em que foi observado: 2º ponto de operação e zonas mortas de 3 e 6 L/min, 17 casos (Tabela S `rate_demand_check`). Os 12 laços com ρ ≥ 1 melhoraram com o gatilho; com ρ < 1, AMIGO melhorou e SIMC piorou. O texto apresenta ρ ≥ 1 como heurística calibrada neste reator, sem ruído e baseada em modelo; "123 de 124" aparece como a amostra de onde a regra saiu, não como validação. |
| 2 Ruído | feito | Sem anti-windup, BC(Tt^cv) e regra direcional, com σ = 0,01 e 0,05 K e 30 realizações (Tabela S `noise_policies`). **Achado:** com 0,05 K, o BC com Tt^cv escolhido sem ruído fica até 51 % pior que a regra para ZN, CC, AMIGO e ITAE ótimo, e melhor para TL e SIMC. A ordem das demais conclusões se mantém. Resumo, conclusão 3, Seção 4.7 e limitações agora dizem "sem ruído". |
| 3 u_act | feito | Frases na Seção 2.3 e nas limitações: o controlador replica sat+taxa; posição medida não foi simulada. |
| 4 Resumo | feito | 236 → 224 palavras. |
| 5 AMIGO | feito | A macro saiu do modo matemático (Seção 4.5 e S3). |
| 6 Carta | feito | `cover_letter_v7.md` (570 palavras) atualizada com ρ heurístico, ruído, u_act e segundo processo. |
| 7 Regra padrão | feito | Seção 3.2: k−1 é a regra padrão porque usa só sinais guardados e é a regra de todos os resultados. |
| 8 Coluna "free" exata | feito | Tabela 6 com "free, exact". Para ZN e CC o mínimo vai ao menor Tt varrido (0,009 e 0,008 min), sem ganho em ±5 K: T_d limita a escolha porque o IAE cai à medida que o rastreamento fica mais forte, e o mínimo em Δt com Euler é artefato. |
| 9 ±0,00 | feito | Tabela do Shapley só com médias; a maior meia-largura (0,006) vai para a legenda e para `sobol_shapley_halfwidth.csv`. As médias são idênticas às da rodada anterior. |
| 10 S2 | feito | Uma tabela (custo do projeto ITAE) e um parágrafo. O resto (tabela nominal com 2-DOF, margens, Fig. S1, erro de modelo, fora da amostra, locus, pesos conjuntos) foi para `repository/S2_tuning_extended.tex`. |
| 11 Segundo processo / stiction | **não feito** | É um estudo novo, fora do alcance desta rodada; fica declarado nas limitações e na carta. |
| 12 | parcial | Pacote Overleaf atualizado e testado numa pasta limpa (main e Suplementar compilam). [16] e [18] confirmadas no IEEE Xplore; [20] confirmada na MDPI. [19]: a ScienceDirect continua bloqueando o acesso automatizado, **confira à mão**. Script não renomeado (data statement). |

Para manter 12 páginas:
- A antiga Tabela 8 (razões em S_max) saiu do texto principal. O mesmo conteúdo está na primeira linha de cada laço da Tabela S `smax_map`, citada no texto. As tabelas seguintes do texto principal foram renumeradas.
- A dedução da cota de D foi para o Suplementar (Eq. S `dbar`); no texto principal ficou uma frase com a referência.
- Os números da zona morta e do 2º ponto de operação na Seção 4.6 foram reduzidos aos essenciais; os demais estão na Tabela 8 (antiga 9).

O segundo rerun falhou na etapa Sobol com "Tcl_AsyncDelete": o backend Tk do matplotlib coletado numa thread do joblib. `build_paper_assets.py` agora fixa o backend `Agg`. O terceiro rerun completo passou em 1329 s; os CSVs só diferem do commit nos itens desta rodada.

Verificação final da rodada:
- PDF: 12 páginas de texto; Suplementar com 18 páginas.
- Referências: nenhuma indefinida; ordem de citação 1–31.
- Caixas estouradas: só as 4 que já vinham da v6.
- Desk-check passou.
- Testes: 157 passed, 1 xfailed; `ruff` limpo.
- Macros: nenhuma macro da v6 mudou; há 121 novas.
