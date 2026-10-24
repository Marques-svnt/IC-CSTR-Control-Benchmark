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
