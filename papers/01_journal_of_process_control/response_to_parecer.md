# Resposta ao parecer editorial da 2ª rodada — Artigo 1 (JPC)

Mapeamento exigência → mudança → onde está. Números vêm de `results/jpc/*.csv`, gerados por `experiments/build_paper_assets.py jpc-remediation`.

## Obrigatórias

| # | Exigência | O que foi feito | Onde |
|---|---|---|---|
| 1 | Reposicionar contra a literatura de AW; "textbook" → clamping de amplitude insensível ao sinal; carta ao editor | Título, resumo (≤250 palavras), destaques e conclusões reescritos em torno do gatilho de taxa; subseção de posicionamento com tabela de famílias; "textbook" removido do texto e das tabelas; carta em `cover_letter.md` | Título, Sec. 1.1, Tab. 1, Sec. 4.3, Sec. 5 |
| 2 | Rotular M_s(FOPTD) e medir o custo da restrição | Rótulo `Optimal ITAE (M_s^FOPTD ≤ 1.6)`; otimização com M_s ≤ 1,6 na linearização exata (ZOH incluído): ótimo interior (M_s^lin = 1,20), ITAE −11,3 %, IAE −3,4 %, K_hf +76 %, TV +22,6 %, sem ganho fora da amostra; "fastest robust PID" retirado | Sec. 3.7, Sec. 4.5, Tab. `constraint_cost` |
| 3 | Ablação: T_t ×0,1/×10; −5, +5 K; carga | Tab. de cenários (−5, +5, carga determinística, 7 políticas) e Tab. de T_t (3 degraus); back-calculation degrada até 38× com T_t ×0,1 ou ×10 | Sec. 4.3, Tab. `antiwindup_scenarios`, `antiwindup_tt_sweep` |
| 4 | Sobol: IC, ponto de partida, faixas, margem de remoção de calor | IC por bootstrap (SALib) na tabela; ponto de partida declarado (equilíbrio nominal); faixas traduzidas em vazão requerida (Eq. `u_req`, Tab. `sobol_ranges`); teste de Spearman IAE × u_req (0,43–0,81); explicação de "baixa margem" para TL/ITAE retirada; CC e ITAE 1-DOF incluídos | Sec. 4.10, Eq. (u_req), Tab. `sobol_sensitivity`, `sobol_ranges`, `sobol_margin_test` |
| 5 | 2-DOF: otimização conjunta | Otimização conjunta de (K_p, T_i, T_d, β, γ) sob cada restrição: β = 1,00/0,98, γ = 0,00/0,09 (volta ao 1-DOF); "2-DOF Optimal" passa a "variante com β = 0,5 fixo" | Sec. 3.7, Sec. 4.5 |
| 6 | Carga: filtro, nº de realizações, sem rank por TV | Tabela determinística (sem ruído, sem filtro) + 30 realizações com e sem filtro (média ± IC95); TV/teto reportado, ranking só por IAE | Sec. 4.7, Tab. `disturbance_rejection_table`, `load_replicated` |
| 7 | Coerência entre artigos; refs [21], [23], [25] | Verificação no Crossref de todas as DOIs dos 3 .bib (`scripts/verify_bib_crossref.py`); frase do Artigo 2 reescrita (fouling é cenário do próprio Artigo 2); título do Artigo 1 atualizado nos 3 .bib | `references.bib` ×3, Artigo 2 Sec. 3 |

## Achados da verificação de referências (não estavam no parecer)

As DOIs de \[23\] (Padula e Visioli) e \[25\] (Reynoso-Jardón et al.) apontavam para artigos de outros assuntos (integridade multivariável; descarga de silos). Substituídas por Padula e Visioli, *JPC* 21(1):69–81, 2011, e Marques e Reynoso-Meza, *IFAC-PapersOnLine* 53(2):7933–7940, 2020. Também estavam erradas ou sem registro: Grimholt e Skogestad (título, páginas, DOI), Tarbouriech e Turner (título, volume, páginas), Bohn e Atherton, Peng et al., Uppal et al., Aris e Amundson, Hedengren et al., Garpinger et al., Alcántara et al. (entrada trocada por Alcántara, Vilanova, Pedret 2013), Alvarez et al. (trocada por Alvarez, Alvarez, González 1989, só nos Artigos 2 e 3) e a ordem de autores de Choudhury et al.

## Recomendadas

| Recomendação | Situação |
|---|---|
| N como variável de projeto; tamanho de efeito | Feito: Tab. `n_design_sweep` (N ∈ {3,5,10}); redução relativa de TV na Tab. de testes pareados; "1920" explicado (480 determinísticas) |
| Pseudocódigo da Eq. (13) e checklist | Feito: Algoritmo 1 e Sec. 3.4 |
| Literatura 2019–2026 | Feito: sete referências, todas com DOI confirmado no Crossref |
| Tab. do Sobol com CC e ITAE 1-DOF; "every tuning" | Feito (7 laços); Conclusão 4 reescrita com os intervalos |
| Resumo ≤ 250 palavras; legendas | Resumo com 248 palavras; legenda da Fig. 3 encurtada |
| ORCID dos coautores | **Pendente (autor):** o ORCID do coautor não está no repositório |
| DOI de arquivo (Zenodo) | **Pendente (autor):** `CITATION.cff` e `.zenodo.json` foram adicionados; o DOI só existe depois de criar o release no GitHub/Zenodo |
| Segundo estudo de caso | **Não feito:** declarado como limitação e trabalho futuro |


---

# 3ª rodada — exigências consolidadas

| # | Exigência | O que foi feito | Onde |
|---|---|---|---|
| 1 | Varrer S_max (20–320) e mapa de regime; proposição do travamento | `run_smax_map`: 6 laços × 5 políticas × 9 valores de S_max (Fig. 4, Tab. 8); Proposição 1 (offset de equilíbrio T_∞ com I ≥ I*) com prova curta, e contraprova para a regra direcional; T_∞ introduzido na Sec. 2.3 | Sec. 2.3, 3.2, 4.3 |
| 2 | Fontes [6, 16] do "cego ao sinal" | Não atribuí a regra a nenhuma fonte: reformulada como erro frequente de implementação (Sec. 1.1, resumo, destaque 1, Tab. 1 sem citação na linha); a regra direcional cita Peng et al. e Hippe como forma "sinal do incremento" | Sec. 1.1, Tab. 1 |
| 3 | Retrocálculo: IAE × T_t, melhor T_t, ZN = CC, "38×" | `run_tt_curve`: curva em [0,525 Δt, 10 T_i] com faixa [T_d, T_i] sombreada (Fig. 3) e tabela do melhor T_t por laço e degrau. ZN = CC (18,56) é efeito de Δt/T_t > 1 (2,14 e 2,36): a válvula fica a menos de 1,6 L/min do viés nos dois. **"38×" retirado** do resumo, destaque e conclusão: dentro de [T_d, T_i] o retrocálculo iguala a regra direcional (≤ 3 % pior, até 34 % melhor) | Sec. 4.3, Fig. 3, Tab. 7 |
| 4 | Sobol: região factível, Δt e horizonte, lógica de AW, "explica grande parte" | Sobol refeito com Δt = 0,02 e 10 min após o degrau (como o benchmark), AW direcional declarado; S₁ por RBD-FAST na região factível (u_req ≤ 300) com IC; ρ² reportado (0,18–0,66); frase "explica grande parte" substituída por "explica parte" | Sec. 4.10, Tab. `sobol_feasible`, `sobol_margin_test` |
| 5 | Erros | "76 % less" → 43 % (Sec. 4.5); "1,8 a 3,1" → 1,8 a 3,3; destaque 5 reescrito (≤ 85 caracteres, verificado pelo desk-check); "Eq. 13" → `\ref` (Eq. 14); sementes da Tab. 17 = as da campanha de ruído; Pareto: título do painel, legenda e tabela passam a falar do "locus SIMC" e da "frente escalarizada", sem "fronteira de Pareto contínua" | Sec. 4.5, 4.9, Tabs. 4–6, 16, Fig. 5 |
| 6 | Resumo e destaques | Resumo com 233 palavras (contagem sem comandos LaTeX) e cinco destaques ≤ 85 caracteres; ganho de 11 % apresentado como "em amostra, sem ganho fora dela" | `main.tex`, `highlights.tex` |
| 7 | Referências, DOI, ORCID, carta | Referências novas: todas com DOI conferido no Crossref (`scripts/verify_bib_crossref.py`); carta explicita a relação com os artigos irmãos. **Pendentes (autor):** DOI de arquivo (release no Zenodo) e ORCID do segundo autor, que não constam no repositório | `cover_letter.md` |

## Recomendadas

| Recomendação | Situação |
|---|---|
| Segundo ponto de operação | Feito: q_j = 150 L/min, FOPTD re-identificado, cinco regras re-sintonizadas (Tab. `antiwindup_second_op`) |
| Comparador de condicionamento; LMI | T_t = T_i (valor associado ao condicionamento) incluído na Tab. 7; ausência do compensador LMI justificada por escrito (Sec. 1.1 e 4.3) |
| Figura do mecanismo | Feita: Fig. 2 (u_raw, u_act, e, I do ZN em três políticas) |
| Erro de modelo ±20 % | Feito para K, τ, θ (27 cantos) e para a malha exata; o ótimo com M_s exato tem M_s^FOPTD até 151,8. **Banda morta e atrito: não simulados** (declarado) |
| Encurtar o Sobol e mover tabelas ao suplementar | **Não feito**: o artigo cresceu para 23 páginas; decidir se vale um arquivo suplementar |
| "Sem parâmetro" qualificado; regime da regulação | Feito (Tab. 1, Sec. 4.3, Sec. 4.7) |
| Separar curvas das Figs. 1 e 3 | Feito: dois painéis (regras empíricas e projetos robustos) |
| Segunda planta de ação reversa | **Não feito** (declarado como trabalho futuro) |


---

# 4ª rodada — exigências consolidadas

| # | Exigência | O que foi feito | Onde |
|---|---|---|---|
| 1 | Retrocálculo com T_t único por laço; ajustar resumo, destaque 3, conclusão 1; reportar T_t = T_i e √(T_i T_d) | Critério minimax (maior razão IAE_retrocálculo/IAE_direcional entre −2, −5, +5 K, em [T_d, T_i]) e critério de validação (escolha no degrau de −2 K, teste em ±5 K); piores razões: 1,02/0,94/0,94/1,00/0,90/1,01 (minimax); √(T_iT_d) até 1,37; T_i até 1,97. Conclusão: dentro de 2 % e até 10 % melhor; o melhor-T_t-por-degrau foi abandonado | Sec. 4.3, Tabs. 7–8, resumo, destaque 3, conclusão 1 |
| 2 | Erro de modelo na mesma planta exata, com τ, estabilidade por canto | 18 cantos por ajuste (ganho, todas as constantes de tempo, atraso extra), estabilidade pelas raízes do polinômio característico (Padé 4); M_s só sobre cantos estáveis. **Nenhum canto instável**; pior M_s: 1,63 (ótimo FOPTD) e 2,06 (ótimo exato). "Colapsa" removido do resumo e da conclusão 3 | Sec. 4.5, Tab. `model_error_ms` |
| 3 | Conclusão 4 e ρ² | Reescrita: ρ_s(TV) = +0,64 e +0,69 (AMIGO, SIMC; ρ² = 0,41 e 0,48), negativa para ZN e CC; ρ² do IAE = 0,18–0,66 | Sec. 4.10, conclusão 4 |
| 4 | Sobol: só 1ª ordem na região factível; limitação | Dito no resumo e na Sec. 4.10: índices de 1ª ordem (RBD-FAST) recalculados; total-ordem indefinido em caixa truncada e com entradas dependentes | resumo, Sec. 4.10 |
| 5 | Linguagem de generalidade | Prop. 1 geral; mapa, comparação e Sobol "do reator estudado" (introdução das conclusões, limitações) | conclusões, Sec. 4.11 |
| 6 | Destaque 4 truncado; resumo | Causa: `%` sem escape em LaTeX comentava o resto da linha; destaques corrigidos (`\%`), desk-check passa. Resumo com 203 palavras (contagem sem comandos). **Não consegui abrir o guia do JPC**; limite não verificado | `highlights.tex`, `main.tex` |
| 7 | Refs, DOI, carta | Refs verificadas por script no Crossref (sem mudanças nesta rodada). **Pendente (autor):** release com DOI (Zenodo) e envio da carta, que já declara a relação com os artigos irmãos | `cover_letter.md` |

## Recomendadas

| Recomendação | Situação |
|---|---|
| Segunda planta independente | **Não feita**; declarada como limitação e trabalho futuro |
| Zona morta e atrito | Zona morta (3 e 6 L/min) simulada para as 7 políticas (Tab. `antiwindup_deadband`); **atrito não simulado** |
| Razão não monotônica do AMIGO; mapa com ganhos reotimizados | Explicação com dados (a válvula nunca chega a um limite de amplitude; a discrepância comando–válvula cai de 111 a 41 L/min entre 45 e 60 L/min²) e Tab. `smax_retuned` (ITAE ótimo reotimizado em cada S_max) |
| Sensibilidade para entradas dependentes | Efeitos de Shapley na região factível (Tab. `sobol_shapley`); sem IC (uma execução) |
| Qualificar "sem parâmetros"; atraso de uma amostra; IC por bootstrap | "Sem parâmetros" qualificado (depende de S_max e Δt); atraso de uma amostra discutido na Sec. 3.2 (não variado); tabelas determinísticas não têm incerteza amostral (dito na Sec. 4.1) |
| Condensar Sobol e tabelas repetidas | **Não feito**: o artigo cresceu para 25 páginas |
