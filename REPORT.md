# REPORT — Artigo 1 (JPC), v7 → v10

A versão vigente é a v10 (seção 9). Seções anteriores que contradizem a v10 estão marcadas como superadas.

Branch `jpc-v7`, criado a partir de `phase4/verification` (43aba62). Sem push e sem tag.

## 1. Tarefas

| Tarefa | Estado | Commit | Observação |
|---|---|---|---|
| T1 Regra direcional e SIMC | feito | 0a1f18a, e5681a2 | Recomendação condicionada a ρ ≥ 1. ρ é a demanda de taxa do laço sem limite de slew dividida por S_max·Δt; é ex-ante (não usa IAE). ρ **não separa** SIMC dos demais (AMIGO a 320 L/min² ganha com ρ = 0,21); vale só como condição suficiente nesta planta. Legendas das Tabelas 8/S10 corrigidas. |
| T2 Tt^sel na fronteira | feito | 285bc05 | ZN e CC na borda inferior (T_d), SIMC na superior (T_i). Mínimo livre: Δt para ZN/CC, 10·T_i (topo da grade) para SIMC. |
| T3 Coluna BC(Tt^sel) | feito | 44980a7 | Coluna nas Tabelas 4, 5, 9, S12 e S13. No 2º ponto de operação, Tt^sel foi re-escolhido pelo mesmo critério. |
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
- T3: com a coluna Tt^sel, "within 10 % of the best back-calculation" (S3, zona morta) deixou de valer; a regra de taxa fica até 19 % pior que BC(Tt^sel). Texto corrigido.
- T10(d): as médias do Shapley mudaram um pouco em relação à rodada única da v6 (ex.: E_a/R do ZN em IAE 0,09 → 0,13; faixa de C_Af 0,43–0,59 → 0,43–0,61).

## 3. Referências

- [19] **Corrigida, mas confira antes de submeter.** O registro Crossref do DOI 10.1016/j.ifacol.2024.08.093 (e o OpenAlex, que o copia) separa errado os nomes: "Inés Tejado Blas" e "M. Vinagre". Esses dois "autores" só existem nesse trabalho, enquanto Inés Tejado (ORCID 0000-0001-5542-348X) e Blas M. Vinagre (ORCID 0000-0001-5039-0738), ambos da Universidad de Extremadura, têm centenas de trabalhos. A ScienceDirect bloqueou o acesso automatizado, então **não conferi no PDF nem na página do editor**. Como o Crossref está errado, o erro pode voltar via gerenciador de referências.
- [16] Lerch et al., ICSTCC 2021, pp. 413–418: confirmada no Crossref.
- [18] Aksland et al., ACC 2022, pp. 1588–1594: confirmada.
- [20] Morohoshi e Deng, Processes 13(5) 1266, 2025: confirmada.
- [2] Hippe 2006: o DOI já existia; ISBN 978-1-84628-322-2 acrescentado ao `.bib`. O estilo `elsarticle-num` não imprime ISBN.
- Nenhuma referência ficou como "não confirmada".

## 4. Decisões em pontos ambíguos

1. **Nome do script.** *(Superado na v10: renomeado para `scripts/jpc_numbers.py`, seção 9.1, R10.)* Mantive `scripts/jpc_v6_numbers.py`, porque renomear exigiria editar o data statement (regra 2). As tabelas condensadas passaram a `v7_*.tex`, e a lista de macros a `results/jpc/v7_numbers.csv`; `v6_numbers.csv` ficou como base do diff. Resolver quando o data statement entrar no escopo.
2. **Referências ao Suplementar.** Usei `\suppref{label}`, gerado de `supplementary.aux` por `scripts/jpc_supp_refs.py`. Um rótulo inexistente interrompe a compilação. Ordem de build: supp → `jpc_supp_refs.py` → main.
3. **T1, critério.** Nenhuma métrica de demanda testada separa o SIMC: pico de demanda, tempo em limite de taxa, discrepância integrada, overshoot sem gatilho. Reportei a regra unilateral ρ ≥ 1 e disse que ela não separa.
4. **T10(d).** Usei 30 sementes da floresta e da partição de CV, em vez de bootstrap, que vaza duplicatas entre folds. O intervalo mede a estabilidade do estimador, não a incerteza amostral do Sobol; legenda e texto dizem isso.
5. **T10(e).** Mantive no S2 a definição dos pesos 2-DOF, porque a Fig. 1 e a Tabela S1 mostram essas variantes, e o teste de erro de modelo (Tabela S5), que é sobre M_s no FOPTD contra a planta exata. Saíram para o repositório: otimização conjunta dos pesos, ITAE fora da amostra e o locus SIMC com a figura e a tabela.
6. **T6.** A equação completa ficou no Suplementar (Eq. S), e o texto principal ganhou uma frase com a referência; não havia espaço.
7. **Espaço.** Para caber em 12 páginas, não cortei conteúdo. Tirei duplicações (números do SIMC já presentes na Seção 4.6 e na Tabela 9; exemplo do TL já na Tabela 7) e passei a Tabela 10 para uma coluna. O detalhe novo de T6, T7 e T8 está no Suplementar, com referência exata.
8. **Fora do pedido, mas consequência do T1** (feito após o parecer do usuário): resumo e highlight 2 agora qualificam o gatilho de taxa ("restores fast loops; it worsens SIMC").

## 5. Verificação final (v7)

Superada: a verificação vigente é a da rodada 9 (seção 8.6).

## 6. Riscos e pendências para o autor (v7)

Superados: os riscos e pendências vigentes estão na seção 8.5.

## 7. Rodada editorial (revisão maior, 62–77)

| Item | Estado | O que foi feito |
|---|---|---|
| 1 ρ | feito | ρ calculado fora da amostra em que foi observado: 2º ponto de operação e zonas mortas de 3 e 6 L/min, 17 casos (Tabela S `rate_demand_check`). Os 12 laços com ρ ≥ 1 melhoraram com o gatilho; com ρ < 1, AMIGO melhorou e SIMC piorou. O texto apresenta ρ ≥ 1 como heurística calibrada neste reator, sem ruído e baseada em modelo; "123 de 124" aparece como a amostra de onde a regra saiu, não como validação. |
| 2 Ruído | feito | Sem anti-windup, BC(Tt^sel) e regra direcional, com σ = 0,01 e 0,05 K e 30 realizações (Tabela S `noise_policies`). **Achado:** com 0,05 K, o BC com Tt^sel escolhido sem ruído fica até 51 % pior que a regra para ZN, CC, AMIGO e ITAE ótimo, e melhor para TL e SIMC. A ordem das demais conclusões se mantém. Resumo, conclusão 3, Seção 4.7 e limitações agora dizem "sem ruído". |
| 3 u_act | feito | Frases na Seção 2.3 e nas limitações: o controlador replica sat+taxa; posição medida não foi simulada. |
| 4 Resumo | feito | 236 → 224 palavras. |
| 5 AMIGO | feito | A macro saiu do modo matemático (Seção 4.5 e S3). |
| 6 Carta | feito | `cover_letter_v7.md` (570 palavras) atualizada com ρ heurístico, ruído, u_act e segundo processo. |
| 7 Regra padrão | feito | Seção 3.2: k−1 é a regra padrão porque usa só sinais guardados e é a regra de todos os resultados. |
| 8 Coluna "free" exata | feito | Tabela 6 com "free, exact". Para ZN e CC o mínimo vai ao menor Tt varrido (0,009 e 0,008 min), sem ganho em ±5 K: T_d limita a escolha porque o IAE cai à medida que o rastreamento fica mais forte, e o mínimo em Δt com Euler é artefato. |
| 9 ±0,00 | feito | Tabela do Shapley só com médias; a maior meia-largura (0,006) vai para a legenda e para `sobol_shapley_halfwidth.csv`. As médias são idênticas às da rodada anterior. |
| 10 S2 | feito | Uma tabela (custo do projeto ITAE) e um parágrafo. O resto (tabela nominal com 2-DOF, margens, Fig. S1, erro de modelo, fora da amostra, locus, pesos conjuntos) foi para `repository/S2_tuning_extended.tex`. |
| 11 Segundo processo / stiction | **não feito** | É um estudo novo, fora do alcance desta rodada; fica declarado nas limitações e na carta. |
| 12 | parcial | Pacote Overleaf atualizado e testado numa pasta limpa (main e Suplementar compilam). [16] e [18] confirmadas no IEEE Xplore; [20] confirmada na MDPI. [19]: a ScienceDirect continua bloqueando o acesso automatizado, **confira à mão**. Script não renomeado (data statement; superado na v10: renomeado, seção 9.1). |

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

## 8. Rodada 9 (v8 → v9), branch `jpc-v9`

### 8.0 Registros feitos antes de simular (regra 8)

**C1 — segunda planta.** Trocador de calor com casco bem misturado (um estado, T_c) e o tubo em duas células (T_1, T_2). **Não é contracorrente.** É um modelo construído para este estudo, não um benchmark publicado; Seborg [6], Shinskey [21] e Luyben [13] só motivam a estrutura.
- **Equações:** as do pedido, com UA(q_c) = UA_0 (max(q_c, 5)/q_c,ss)^0,8. A saída é y(t) = T_2(t − 0,20 min), implementada como FIFO de 10 amostras com Δt = 0,02 min.
- **Parâmetros:** os do pedido, sem alteração. V_p = 100 L, V_c = 40 L, q_p = 100 L/min, T_p,in = 390 K, T_c,in = 300 K, ρC_p = 500 cal/(L·K) dos dois lados, UA_0 = 6,0×10⁴ cal/(min·K), q_c,ss = u_bias = 100 L/min.
- **Atuador e controlador:** o mesmo atuador ([0, 300] L/min, S_max = 80 L/min², Δt = 0,02 min), o mesmo PID e as mesmas políticas.
- **Atraso:** não será ajustado para atingir um r = θ/τ desejado; r será medido e reportado.
- **Métrica:** o IAE é calculado sobre y, a saída da planta incluindo o transporte de 0,20 min, porque é essa a variável definida como saída.
- **Identificação:** degrau de +10 L/min em q_c.
- **Sintonia:**
  - ZN, CC, TL, AMIGO e SIMC (τ_c = 0,4 min) pelas mesmas fórmulas.
  - ITAE ótimo **reotimizado** nesta planta pelo mesmo procedimento do CSTR: Nelder–Mead, ITAE do degrau de −2 K em 6 min, penalidade 10⁴ max(0, M_s^FOPTD − 1,6)², partidas no palpite padrão e nas regras analíticas com M_s ≤ 1,6.
- **Degraus:** −2, −5 e +5 K. Antes de simular, confiro se cabem na faixa da válvula; se não couberem, ajusto e registro.
- **Critério de escolha:** nenhum parâmetro é escolhido pelo resultado das políticas. Se a planta não reproduzir as verificações do pedido (autovalores, T_2,ss, T_2 em q_c = 300, sinal do ganho), registro a divergência e sigo com o modelo como especificado.

**C2 — segundo ponto de operação do CSTR.**
- **Candidatos:** q_j,ss ∈ {40, 55, 70, 200, 250} L/min. Descarto, com registro, qualquer ponto instável em malha aberta ou com estados múltiplos.
- **Critério, aplicado antes de simular as políticas:** menor folga até o batente superior, (u_max − q_j,ss)/u_max. Em caso de empate prático (diferença de folga < 0,05), vence o de maior |K| do FOPTD.
- **Protocolo:** re-identificar o FOPTD e re-sintonizar as regras analíticas, sem reotimizar o ITAE. Depois, 7 políticas em −2 e ±5 K, mais ρ.

**C2 — candidatos avaliados antes de simular as políticas** (`results/jpc/c2_candidates.csv`, função `select_c2_point`):

| q_j,ss (L/min) | T_ss (K) | folga | K (K/(L/min)) | autovalor lento (min⁻¹) | estados estacionários |
|---|---|---|---|---|---|
| 40 | 415,16 | 0,867 | −0,449 | −1,160 | 1 |
| 55 | 408,74 | 0,817 | −0,342 | −1,267 | 1 |
| 70 | 403,80 | 0,767 | −0,272 | −1,368 | 1 |
| 200 | 384,13 | 0,333 | −0,080 | −3,346 | 1 |
| 250 | 380,61 | 0,167 | −0,060 | −2,472 | 1 |

- Todos os candidatos são estáveis e têm estado estacionário único. A primeira contagem dava 2 estados em todos porque contava a troca de sinal no polo de u_req(T) (T_j* = T_jf, perto de 350 K). Corrigi para contar só raízes entre vizinhos fisicamente válidos (0 ≤ u_req < 10⁴).
- Pelo critério registrado, o escolhido é **q_j,ss = 250 L/min**, sem empate: o segundo colocado tem folga 0,333.

**D1 — protocolo da auditoria da literatura (registrado antes de buscar).**
- **Base de busca:** OpenAlex (API pública, ordem de relevância da própria base). Texto completo lido no site do editor ou em PDF de acesso aberto, quando acessível. Scopus e Google Scholar não estão acessíveis neste ambiente (sem credencial; o Scholar exige CAPTCHA, que não contorno). A ScienceDirect bloqueia acesso automatizado; registro cada bloqueio.
- **Janela:** 2015–2026 (filtro `publication_year:2015-2026`, tipo `article`).
- **Strings de busca, exatas e nesta ordem:**
  1. `CSTR control comparison actuator saturation`
  2. `continuous stirred tank reactor temperature control comparison PID MPC constraints`
  3. `CSTR controller comparison input constraints`
- **Inclusão:** comparação de estratégias de controle num CSTR (ou reator químico equivalente) com alguma restrição de atuador mencionada na metodologia.
- **Seleção:** os primeiros resultados que atendam à inclusão, na ordem da base, percorrendo as strings em sequência, sem filtrar por resultado, até 12–15 artigos lidos no texto completo. Artigo cujo texto completo não abra entra como "resumo apenas" e não é contado.
- **Itens codificados** (sim / não / não aplicável / não verificável):
  1. modelo de atuador declarado (amplitude, taxa, folga);
  2. lógica anti-windup declarada;
  3. sinal de ação do laço explícito;
  4. Δt e método de discretização do controlador declarados;
  5. caminho de medição (ruído, filtro) declarado.
- **Método de leitura:** busca por palavras-chave no texto completo (saturation, rate, slew, windup, anti-windup, sampling, discret, Euler, noise, filter, reverse, direct acting) e leitura dos trechos encontrados. É uma codificação de um executor, sem segundo codificador.
- **Saída:** `papers/01_journal_of_process_control/repository/literature_audit.csv` (lista completa) e uma tabela agregada no Suplementar.

### 8.1 Itens da rodada 9

| Item | Estado | Commit | Observação |
|---|---|---|---|
| Base v8 | feito | 2261b3b | Valores das macros da v8 em `results/jpc/v8_numbers.csv`; o script grava `v9_numbers.csv`. |
| A1 | feito | 4f6e6f6 | "12 pares laço–condição de 5 laços"; 3 casos perto do limiar (ρ < 2), por macro. |
| A2 | feito | 4f6e6f6, 982e7e0 | Highlight 4 e contribuição com "sem ruído"; o achado de ruído virou o highlight 5 (73 caracteres). |
| A3 (a) | feito | 4f6e6f6 | ZN em 240 L/min² trava no batente **inferior** (5,38 min fechada, espelho da Proposição 1); reator a +54,2 K e ainda subindo em t_f. Diagnóstico em `smax_signblind_diagnostics.csv`. |
| A3 (b) | feito | 4f6e6f6 | Diferenças da Tabela 6 de até 0,08, só no SIMC (piora); ≤ 0,01 nos demais. |
| A3 (c) | feito | 4f6e6f6 | Símbolo R = IAE_amp/IAE_rate definido na primeira ocorrência da 4.5 e usado depois. |
| A4 | **não feito** (pendência) | — | [19] continua inacessível; tentativas na seção 8.5. |
| A5 | feito | 4f6e6f6, 982e7e0, 6dba845 | Resumo com 232 palavras (expressão matemática = 1 palavra). Das 4 caixas herdadas, 3 resolvidas; a dos highlights (123,6 pt) aparece num documento mínimo com o `cas-dc.cls` intocado, então é do template e só some alterando a classe. |
| A6 | feito | 6360544 | `cover_letter_v9.md`, 601 palavras. |
| B1 | feito | 0356731 | Tt sob ruído sobe para ZN, CC e AMIGO; o gap estreita (−2 K: 1,51 → 1,29) mas não fecha. |
| B2 | feito | 0356731 | Hipótese sustentada: mesma fração de cortes nas duas políticas; o termo de rastreamento injeta 2,9–4,0 L/min por amostra e o integrador se desvia 5–7 vezes mais. |
| B3 | feito | 0356731 | ρ sem filtro a 0,05 K erra 3 de 18 casos (SIMC ρ até 2,92); com filtro, 0 erros. |
| B4 | feito | 0356731 | Com o filtro, o pior BC/regra cai de 1,50 para 1,15; sem anti-windup fica ≥ 19 vezes pior para ZN e CC. |
| D2 | feito | 79c7c84 | (i) taxa antes da saturação: sem mudança (≤ 6,3 %). (ii) folga antes da taxa, (iii) derivada sobre a medição bruta com ruído e (iv) filtro por Euler: mudam ordenações. 9 das 11 trocas de política são entre a regra e os BCs; as conclusões principais não se invertem. |
| C1 | feito | 2c0b44a, 949e2db | Trocador construído para o estudo. Verificações do pedido reproduzidas; r = θ/τ **medido = 0,34**. Ver seção 8.2. |
| C3 | feito | dc43592 | Stiction de Choudhury (S, J) após a taxa: hunting em 86 % (moderada) e 92 % (severa) das rodadas das políticas que funcionam; latch e windup só-amplitude se mantêm; BC/regra fica errático (0,37–1,61). |
| C4 | feito | fb36c16 | Posição medida sem banda: 49–54 % de congelamentos espúrios e +77 % de IAE (SIMC); com ε_u = 1,7 L/min: ≤ 16 % e IAE a até 3 % da base; BC perde até 10 %. |
| C2 | feito | 02fd99e, 56164e0 | Critério escolheu 250 L/min (folga 0,167). −5 K é inviável ali (exige 355 L/min); em +5 K a ordenação se mantém; ρ ≥ 1 seguido de melhora em 6 de 9 casos (2 empates, 1 perda: TL). |
| D1 | feito | 23a2828, 3b42532 | 66 candidatos; 12 lidos e contados; 14 só resumo (acesso bloqueado). Ver seção 8.2. |
| Bloco 0 | feito | 982e7e0 | Enquadramento, contribuições, resumo, highlights, checklist (ordem dos limites e discretização do filtro, porque D2 mostrou efeito), conclusões. |
| 12 páginas | feito | 6dba845 | Movidos para o Suplementar, com referência exata: Tabela 5 (cenários), Tabela 7 (viagem/overshoot), Fig. 1, Fig. 4, tabela de cargas (duplicava a S) e a frase do C2. Nenhum conteúdo cortado. |

### 8.2 Divergências entre o pedido e os CSV (prevaleceu o CSV)

- **C1, θ/τ:** o pedido estimava r ≈ 0,37; o medido é **0,341** (K = −0,2036 K/(L/min), τ = 0,657 min, θ = 0,224 min).
- **C1, clamping cego:** o pedido supunha que o travamento da Proposição 1 seria "possível". Ele **não ocorre** nos degraus testados: as hipóteses não são atingidas porque ZN e CC oscilam pelo limite de taxa sem parar num batente. O clamping cego ainda fica 1,03–1,23 vezes pior que sem anti-windup.
- **C1, heurística ρ:** não transfere. O gatilho piora o TL em todos os degraus e limites (R até 0,60, mesmo com ρ até 25); ρ ≥ 1 seguido de melhora em 104 de 129 casos.
- **C2:** a verificação inicial de multiplicidade contava 2 estados em todos os candidatos, por causa do polo de u_req(T); corrigido (seção 8.0). Todos os candidatos são estáveis e têm estado único, o que confirma a sua verificação.
- **C3:** as hipóteses de ciclo-limite e de preservação da ordenação foram medidas. Hunting quase sempre; a ordenação entre regra de taxa e BC **não** se preserva (razão 0,37–1,61); o latch e o windup só-amplitude se preservam.
- **D1:** o protocolo pedia 12–15 artigos lidos; o máximo alcançável com as três strings registradas foi **12**. Não acrescentei strings depois de ver os resultados.
- **A3(a):** o +54,2 K não é oscilação; é o travamento espelhado no batente inferior.

### 8.3 Decisões em pontos ambíguos

1. **C1:** o IAE é medido em y = T₂(t − 0,20), a saída definida da planta. Integração por RK4 de passo fixo (4 subpassos por amostra), registrada no código e no Suplementar. **Não afirmo** que o integrador da planta tenha efeito semelhante ao do Euler no BC; não foi testado (restrição 0.6).
2. **C1:** o ITAE ótimo foi reotimizado no trocador sem a reotimização extra ("restart") usada em parte do CSTR. Segui o procedimento de `setup_controllers`, que é o que define o ITAE ótimo da Tabela 3.
3. **C3:** horizonte de 20 min (em vez de 10) para dar tempo ao ciclo-limite. Critério de hunting declarado antes de ver os dados: pico a pico de T > 0,05 K **e** pelo menos 2 deslizamentos nos últimos 10 min. A válvula começa parada e a primeira partida exige S (tratada como reversão).
4. **C3, SIMC:** o "sem anti-windup" do SIMC é aproximado pela política só-amplitude, que coincide com ela porque o SIMC não atinge a amplitude. A política "None" não está entre as 5 da Tabela 8.
5. **C4:** "congelamento espúrio" = integrador parado numa amostra cuja anterior estava em regime linear segundo o modelo interno da válvula.
6. **D2:** "muda" = um par (de laços sob uma política, ou de políticas num laço) inverte de posição com diferença > 1 % nas duas condições. Na variante (ii), o anti-windup continua vendo rate(sat(u_raw)), e só a entrada da planta muda.
7. **D1:**
   - Codificação feita por busca de palavras-chave no texto completo e leitura dos trechos, por um único leitor.
   - Os itens 4 (Δt **e** método) e 5 exigem declaração explícita.
   - Anti-windup é "não aplicável" para MPC.
   - O artigo 1.25 (tanque de qualidade de água modelado como CSTR) foi excluído por não ser reator químico.
8. **Tabela 8 da v8:** já tinha ido para o Suplementar na rodada anterior. Nesta rodada, a numeração do texto principal mudou de novo com as saídas acima.
9. **Highlights:** saíram o do mapa de S_max e o de |K_p|(1+N), substituídos pela dependência da implementação e pelo achado de ruído; |K_p|(1+N) continua nas contribuições, na Seção 4.7 e nas conclusões.

### 8.4 Evidência de cada frase do Bloco 0

*Superada em parte pela seção 9: a frase da auditoria saiu do resumo e foi recodificada (9.2), e a frase sobre Euler e folga foi reescrita com os percentuais da Tabela S15 (9.1, O3c).*

| Frase (onde) | Evidência |
|---|---|
| "in a short audit of 12 articles … none a slew-rate limit or the action of the loop … 2 of the 7 with integral action the anti-windup logic … 2 the sampling interval and the discretization" (Introdução e resumo) | Tabela S `literature_audit`; macros `\vlitcounted`, `\vlitactuatormodel`, `\vlitratelimit`, `\vlitloopsign`, `\vlitantiwindup`, `\vlitantiwindupapp`, `\vlitdtandmethod` |
| "in a computational benchmark these choices can decide the ranking of controllers" (Introdução) | Tabela 4 (sign-blind, gatilho), Tabela 6 (constante do BC), Tabela S `order_variants` (macros `\vorderTworank`, `\vorderFourrank`) |
| contribuição 1: Euler contra exato no rastreamento e no filtro, posição da folga mudam rankings; saturação/taxa não | Tabela S `exact_backcalc` (`\vexZNeuler`, `\vexZNexact`); `order_variants` (`\vorderOnedIAE`, `\vorderOnerank` = same; `\vorderTworank`, `\vorderFourrank` = changes) |
| contribuição 2: hipóteses não atingidas na segunda planta | Tabela S `hx_ablation` (tempo em u_max = 0; checado em `hx_numbers`) |
| resumo: "restores the high-gain loops but worsens slow ones such as SIMC" | Tabelas 4 e 8; Seção 4.5; macros `\vSIMC…`, `\vhxTLratemin` |
| resumo: "with 0.05 K sensor noise it is up to 51 % worse" | Tabela S `noise_policies`; `\vnzbchimaxpct` |
| resumo: "Explicit Euler discretization of the measurement filter and the position of the backlash change the rankings" | `order_variants`; `\vorderFourdIAE`, `\vorderTwodIAE` |
| resumo: "heat exchanger … no latch and a loop where the rate-demand heuristic fails" | Tabela 9 (`v9_hx`) e S `hx_ablation`; `\vhxnrhohihelp`, `\vhxnrhohi`, `\vhxbadrhomax` |
| checklist itens 2 e 5 (ordem; discretização do filtro) | `order_variants` |
| A sentença "we do not claim a survey" foi substituída pelas contagens da auditoria, que a sustentam para a amostra lida; nenhum artigo é nomeado como exemplo negativo no texto principal. | `repository/literature_audit.csv` |

### 8.5 Riscos e pendências para o autor

*Superada pela seção 9.6 (pendências vigentes).*

- **[19] (A4):** volume e páginas 58(7) 388–393 vêm do Crossref e do OpenAlex. Os autores (I. Tejado, B. M. Vinagre) vêm dos registros ORCID, porque os metadados do DOI separam errado os nomes.
  - Tentativas nesta rodada: página e PDF na ScienceDirect (bloqueio/403), doi.org → linkinghub (bloqueio), repositório da UEx (403), OpenAlex (sem texto completo em repositório), Semantic Scholar (429).
  - **Confira no PDF da editora antes de submeter.**
- **Script:** o nome `jpc_v6_numbers.py` continua fora de escopo (data statement).
- **Caixa de 123,6 pt na página de highlights:** é do template `cas-dc` 2.4.
- **D1:** amostra pequena (12), não sistemática, um único codificador; 14 candidatos só com resumo. As frases do texto se limitam aos artigos lidos.
- **C1:** planta construída por nós. Os resultados no trocador são "consistent with" o mecanismo para os laços de alto ganho e contrariam a transferência de ρ e do latch.
- **ρ:** continua heurística. Errou no trocador (TL) e no ponto de 250 L/min (TL em −2 K).
- **Noise:** só σ = 0,01 e 0,05 K e um filtro (τ_m = 0,05 min).
- **Pacote Overleaf:** atualizado e testado nesta rodada (seção 8.6).

### 8.6 Verificação final da rodada 9

*Superada pela seção 9.5 (verificação da v10).*

1. **PDF:**
   - Texto principal em **12 páginas** ("Page 12 of 12"; 13 no PDF com a página de highlights).
   - Resumo com 232 palavras, contando cada expressão matemática como uma palavra.
   - Highlights: 5 itens, com 83, 77, 72, 80 e 73 caracteres.
   - 6 palavras-chave.
   - Referências 1–31 em ordem de primeira citação; nenhuma referência indefinida em main e Suplementar.
   - Desk-check Elsevier passou.
   - Única caixa estourada: a do template (123,6 pt), sem caixas novas. Suplementar com 25 páginas, sem caixas estouradas.
2. **Rerun do zero** (`build_paper_assets.py jpc-remediation` com todas as etapas novas, 1464 s; depois `jpc_v6_numbers.py`):
   - Todos os CSVs, tabelas e PNGs ficaram **idênticos** aos commitados (diff vazio).
   - `generated/numbers.tex` reproduz a partir dos CSVs.
3. **Diff de macros v8 × v9:** nenhuma das 282 macros da v8 mudou de valor ou foi removida; 117 novas (399 no total), cada uma ligada a um item da seção 8.1.
4. **Consistência:**
   - `check_main_supp_consistency.py`: 13 itens, sem divergência.
   - `check_text_numbers.py`: só 0,525 (constante da grade de T_t) fora dos CSVs.
5. **Testes:** `pytest` com 168 passed e 1 xfailed (o xfail do TL, pré-existente); `ruff check .` limpo. Testes novos:
   - trocador de calor: estado estacionário, autovalores, ganho reverso por hypothesis, RK4;
   - stiction: transparência, reversão com salto, posição dentro dos batentes por hypothesis;
   - posição medida: congelamento espúrio sem banda e não com banda;
   - variantes do D2: ordem `rate_sat`, ordem inválida, `d_measurement`.
6. **Overleaf:** `ready-to-overleaf/` e `ready_to_overleaf.zip` atualizados; main e Suplementar compilam numa pasta limpa (12 + 1 e 25 páginas, sem referências indefinidas).

## 9. Rodada 10 (v9 → v10, versão final para o orientador), branch `jpc-v9`

Regra desta rodada: nenhuma simulação nova e nenhum número de resultado novo. Todas as tabelas foram re-renderizadas a partir dos CSV existentes (`scripts/jpc_numbers.py`; a S15 por `exp02.export_latex_table` sobre `results/jpc/order_variants.csv`).

### 9.1 Itens

| Item | Estado | Onde | Observação |
|---|---|---|---|
| O1a | feito | `cover_letter_v10.md` | "are under review elsewhere" → "are in preparation for submission"; títulos e revistas mantidos; frase de não sobreposição mantida. Manuscrito sem nenhuma menção aos irmãos (grep). |
| O1b | feito | carta; símbolo em main, Suplementar, tabelas, CSV, scripts, REPORT | Carta: "selected on the design step and judged on ±5 K steps". O manuscrito nunca dizia "cross-validation" para T_t; as ocorrências que restam são a validação cruzada real da floresta do Shapley. Símbolo T_t^cv → **T_t^sel** por substituição scriptada (`mathrm{cv` → `mathrm{sel`, cabeçalho `cv: ±5 K` → `sel: ±5 K`, `Tt^cv`/`BC^cv` → `Tt^sel`/`BC^sel`) em 43 arquivos; v6/v8_numbers.csv (bases históricas) e cartas antigas não foram tocados. Identificadores internos (`tt_cv`, `BC_CV`, macros `\vttcv…`, rótulo `tab:noise_ttcv`) **mantidos**: não aparecem no PDF e renomeá-los não muda nada para o leitor. |
| O1c | feito | carta, item 5 | Reflete a recodificação: 66 candidatos, 12 lidos, 14 só resumo, um codificador; "none of the 7 whose control law is not purely predictive states the action of the loop". |
| O1d | feito | carta | (1) "a measured valve position" saiu da lista da ablação (só regra de taxa e BC rodaram com posição medida, S17); (2) item 4 com os percentuais da S15 e a menção à tabela de robustez; (3) "released" → repositório público + DOI Zenodo a atribuir (como no data statement); (4) título do item 3 reescrito. |
| O2a | feito | `repository/literature_audit.csv`, Tabela S36, Introdução, Suplementar S8 | Ação do laço = "not applicable" nos 5 artigos puramente preditivos (1.12, 2.9, 2.20, 3.6, 3.13). Contagens em 9.2. **Divergência com o pedido:** os 7 restantes **não são todos PID** (backstepping adaptativo, sliding mode, PSO, PID×MPC, FOPID); o texto diz "the 7 whose control law is not purely predictive", não "com PID". |
| O2b | feito | resumo | Auditoria fora do resumo; 1ª frase abre com o problema (laço reverso, limites de amplitude e taxa, anti-windup, discretização, ordem de avaliação). Na Introdução, com "not systematic and coded by one reader", 66, 12, 14. |
| O2c | feito | `repository/audit_coding.csv` | Um artigo por linha: id, DOI, ano, periódico, tipo e classe de controlador, 7 itens, `second_coder` vazio. Periódicos do Crossref; o 1.8 (sem DOI) do OpenAlex. A classe do 2.3 é "mixed" (PID e MPC). `jpc_numbers.py` agora falha se o arquivo divergir de `literature_audit.csv`. Citado na legenda da S36 e no texto da S8. **Não** declarei segundo codificador. |
| O3a | feito | Seção 4.6 | "Actuator model, implementation and operating points": 4.6.1 Actuator model: deadband and stiction; 4.6.2 Order of evaluation and discretization; 4.6.3 Operating points. Cada uma abre com a pergunta (em itálico) e fecha com "In short, …". Mesmos números e tabelas. A posição da folga foi para 4.6.1 (é especificação do atuador). Contribuição 1 continua citando 4.3–4.7, que existem e dizem o afirmado. |
| O3b | feito | Introdução, contribuição 1, S15, conclusão 1, carta | Dois grupos: (i) escolhas do controlador; (ii) especificação do modelo do atuador, declaradas como propriedades da planta/atuador. Na S15 a coluna chama-se `group` com valores **controller/actuator**, e não "(i)/(ii)", porque a S15 já numera as variantes (i)–(iv); usar (i)/(ii) nas duas colunas confundiria. Variantes (i), (iii), (iv) = controller; (ii) = actuator. |
| O3c | feito | highlight 3, resumo, contribuição 1, conclusão 1 | A S15 sustenta: a folga antes da taxa muda o IAE em até 44,2 % e muda a ordem de laços e de políticas; Euler no filtro, 24,2 % sem ruído, idem; nenhum troca o "vencedor" global, e as trocas de política são 9 de 11 entre regra e BCs. Highlight: "Backlash placement and filter discretization shift IAE by up to 44.2% and 24.2%" (79 caracteres; percentuais por macro). |
| O3d | feito | 4.6.2 | "With Δt/τ_m = 0.4 the explicit Euler filter is a poor discretization, so a difference of this size is an expected warning, not a finding". Resultado mantido. |
| O4 | feito | Tabela 8 (texto principal, Seção 4.9) + parágrafo de recomendação | 6 conclusões × 7 condições; células "holds / in part / fails / not tested" com a tabela/seção; notas a–k explicam cada "in part"/"fails". Sem número de resultado na tabela. |
| O5 | feito | `references.bib` | [19] confirmada no Crossref: IFAC-PapersOnLine 58(7) 388–393, DOI 10.1016/j.ifacol.2024.08.093 (já estava completa). Acrescentados, confirmados no Crossref: DOI de [1] Åström e Rundqwist 1989 (10.23919/ACC.1989.4790464, pp. 1693–1698 conferem); número 5 e DOI de [11] Cohen e Coon (10.1115/1.4015451); DOI de [10] Ziegler e Nichols (10.1115/1.4019264). Pendências em 9.6. |
| R6 | feito | conclusão 2 | Frase das seis condições dividida em duas, e a frase do S_max em duas; conteúdo igual. |
| R7 | feito | início do Suplementar | Índice "conclusão → tabelas/seções". Sem número de tabela, para não renumerar S1–S36. |
| R8 | parcial | — | Sem caixas estouradas novas; a de 9,6 pt da Tabela 8 foi corrigida na hora. A de 123,6 pt continua: é uma hbox **vazia** (`[] []`) emitida pelo `cas-dc` 2.4 no `\maketitle` (aparece num documento mínimo). Tentei `\hfuzz` local: não pega, porque a caixa é detectada no shipout; reverti. Só some editando a classe, o que não fiz. Os 5 avisos "Citation multiply defined" do Suplementar já existiam na v9 (compilei a v9 numa pasta limpa: mesmos 5); vêm do `xr`; a numeração das citações do Suplementar está correta (conferido no PDF). |
| R9 | feito | este arquivo | Cabeçalho, 4.1, 7 (item 12), 8.4, 8.5, 8.6 marcados como superados; seção 9 nova. |
| R10 | feito | `scripts/jpc_numbers.py` | `git mv` + troca em main.tex (data statement), 04_results, README, pyproject, `check_text_numbers.py`, `check_main_supp_consistency.py`. Grep sem ocorrências nos arquivos ativos; sobram só em documentos históricos (CHANGELOG, respostas antigas, diff_v5_v6, parecer_r6, seções antigas deste REPORT). Macros idênticas após o rerun. |
| R11 | feito | 9.7 | — |

**Commits da rodada 10** (branch `jpc-v9`, sem push):

| Commit | Itens |
|---|---|
| 48543af | O1b (símbolo T_t^sel, substituição scriptada) |
| 466fb7b | O2a, O2c (recodificação e `audit_coding.csv`) |
| a4487e0 | O3b (coluna `group` da S15) |
| d8a1625 | O2b, O3a–d, O4, R6, R7 e as movidas para o Suplementar (os itens tocam os mesmos parágrafos) |
| 1866b84 | O5 |
| d7baf37 | R10 |
| 3b5caa1 | O1a, O1c, O1d (carta) |
| 1eee45b | pacote Overleaf e arquivos gerados |
| (este) | R8, R9, R11 (REPORT) |

Nos arquivos com mudanças de mais de um item, cada commit recebeu a versão intermediária só com a mudança do seu item (por exemplo, o commit O1b contém só a renomeação; o nome do script só muda no commit R10).

**Movido para o Suplementar (para manter 12 páginas):**
- Seção 4.9 da v9 (perturbações de carga): o conteúdo já estava na S5 com mais detalhe; no texto principal ficou uma frase de ponteiro na Seção 4.1.
- Fig. 3 da v9 (IAE × T_t): agora Fig. S2, citada na Seção 4.4 como "Supplementary Fig. S2". As figuras do Suplementar foram renumeradas (smax S2→S3, ruído S3→S4, cargas S4→S5, Sobol S5→S6); as referências são geradas.
- Nada foi cortado.

**Outras correções de texto feitas no caminho:**
- Suplementar, parágrafo da zona morta: "Stiction was not modelled." contradizia a S16; trocado por um ponteiro ao parágrafo de stiction.
- Legendas da S3 e da S27 apontavam para a Seção 4.9 removida; agora apontam para a S5.1 (também no gerador).
- Parágrafo de síntese da 4.9: a primeira versão dizia que "o latch vale em toda condição do reator"; corrigi para "o clamping cego fica muito pior… (o latch só foi checado onde marcado)", como a Tabela 8 sustenta, e acrescentei a exceção do ρ em 250 L/min.

### 9.2 Auditoria: contagens antigas e novas

| Item | v9 (sim/não/n.a./n.v.) | v10 (sim/não/n.a./n.v.) |
|---|---|---|
| Limites do atuador (amplitude) | 11/1/0/0 | 11/1/0/0 |
| Limite de taxa | 0/12/0/0 | 0/12/0/0 |
| Folga ou zona morta | 0/12/0/0 | 0/12/0/0 |
| Lógica anti-windup | 2/5/5/0 | 2/5/5/0 |
| **Ação do laço** | **0/12/0/0** | **0/7/5/0** |
| Δt e método de discretização | 2/10/0/0 | 2/10/0/0 |
| Ruído ou filtro de medição | 1/9/0/2 | 1/9/0/2 |

Frases que dependiam disso:
- v9, resumo: "none stated a slew-rate limit or the action of the loop". Removida (auditoria fora do resumo).
- v9, Introdução: "none a slew-rate limit or the action of the loop" (sobre 12). Agora: limite de taxa sobre 12; ação do laço e anti-windup sobre os 7 não puramente preditivos.
- Carta, item 5: idem.

### 9.3 Decisões em pontos ambíguos

1. **"n = 7 com PID":** a codificação não confirma. Só 3 dos 7 têm PID (1.10, 2.3, 3.25). Escrevi "whose control law is not purely predictive".
2. **Rótulos dos grupos na S15:** controller/actuator (ver O3b).
3. **Robustez, "matches":** li "BC(T_t^sel) iguala a regra" como "não fica pior além do que já fica no caso nominal". Com zona morta, BC^sel fica no máximo ~2 % pior (Optimal ITAE, −2 K) e melhor nos demais: marquei "holds". Com posição medida, há pares laço–degrau em que BC fica alguns por cento pior que a regra com banda: marquei "in part".
4. **Latch sob ruído e em outros pontos:** a tabela distingue "clamping cego muito pior" (medido) de "latch" (não checado): "in part", com nota.
5. **Highlight 3:** usei as macros (44.2, 24.2) em vez de arredondar para 44/24, para não digitar número.

### 9.4 Evidência das frases novas

| Frase nova | Evidência |
|---|---|
| Introdução: 66 / 12 / 14 / 11 / 2 / 7 / 2 | macros `\vlitcandidates`, `\vlitcounted`, `\vlitabstract`, `\vlitactuatormodel`, `\vlitdtandmethod`, `\vlitloopsignapp`, `\vlitantiwindup` (S36) |
| Resumo, highlight 3, conclusão 1: 44,2 % e 24,2 % | S15; `\vorderTwodIAE`, `\vorderFourdIAE` |
| 4.6.2: Δt/τ_m = 0,4 | Δt = 0,02 min, τ_m = 0,05 min (parâmetros declarados; `check_text_numbers.py` lista 0.4 como constante, não resultado) |
| Tabela 8, cada célula | tabela/seção citada na própria célula (conferidas uma a uma em 9.5, item 5) |

### 9.5 Autoverificação

**1. Números das tabelas, antes × depois** (`snap.py`: todo número de `tables/*.tex` por arquivo, mais todas as macros de `generated/numbers.tex`; 3511 → 3522 linhas):
```
657a658,667
> conclusion_robustness.tex  -2 1 | -5 1 | 1 1 | 1.72 1 | 150 3 | 2 1 | 250 4 | 3 1 | 3.5 1 | 7 1
1046c1056  < literature_audit.tex 0 15   > literature_audit.tex 0 14
1050c1060  < literature_audit.tex 12 3   > literature_audit.tex 12 2
1053c1063  < literature_audit.tex 5 2    > literature_audit.tex 5 3   > literature_audit.tex 7 1
3457c3468  < macro litloopsignna 0        > macro litloopsignna 5
3458c3469  < macro litloopsignapp 12      > macro litloopsignapp 7
```
Justificativa: (a) `conclusion_robustness.tex` é nova e qualitativa; os "números" são larguras de coluna (1.72, 3.5), pontos de operação (150, 250), degraus (−2, −5), "Proposition 1", "two of the three" etc.; nenhum resultado. (b) `literature_audit.tex` e as macros `litloopsign*`: recodificação deliberada do O2a. Nenhum outro número mudou. Depois só da renomeação T_t^cv → T_t^sel, o diff foi **vazio**.

**2. grep** (`under review|cross-validation|cross-validated|systematic|none of the|T_t^cv|mathrm{cv`) em main, highlights, Suplementar, seções, tabelas, generated, carta v10, CSV da auditoria, `jpc_numbers.py`, `build_paper_assets.py`:
- `supplementary.tex:256`, `tables/sobol_shapley.tex`, `build_paper_assets.py:1764/2039–2042`: "cross-validated"/"cross-validation" da floresta aleatória do Shapley. **Correto** (é validação cruzada de fato).
- `01_introduction.tex:3`, `supplementary.tex:286`, `tables/literature_audit.tex`, `jpc_numbers.py:982`, carta linha 16: "not systematic"/"not a systematic review". **Correto.**
- carta linha 29: "reuses none of their tables or figures". **Correto.**
- `under review`, `T_t^cv`, `mathrm{cv`: **nenhuma ocorrência.**

**3. Contagens:**
- Resumo: **247 palavras** com um contador mais estrito (cada expressão matemática = 1 palavra, "K·min" conta à parte; o mesmo contador dá 236 para a v9, que o REPORT 8.6 dava como 232).
- Highlights: 83, 77, **79**, 80, 73 caracteres (com espaços, macros expandidas).
- Texto principal: **12 páginas** ("Page 12 of 12"; 13 no PDF com a página de highlights). Suplementar: **26 páginas** (25 na v9; +índice e +Fig. S2).

**4. Compilação** (main → Suplementar → `jpc_supp_refs.py` → main → Suplementar; também numa pasta limpa a partir de `ready_to_overleaf.zip`):
- "??" no texto dos dois PDFs: 0. Referências indefinidas: 0. Citações faltando: 0.
- Caixas estouradas: só a do template (123,6 pt, vazia; ver R8). Suplementar sem caixas estouradas.
- Avisos remanescentes: 5 "Citation multiply defined" no Suplementar, pré-existentes (ver R8).
- Desk-check Elsevier: passou. `ruff check .`: limpo. `pytest`: **168 passed, 1 xfailed** (o xfail do TL, pré-existente).
- `check_main_supp_consistency.py`: 13 itens sem divergência. `check_text_numbers.py`: só 0,525 fora dos CSV no Suplementar.

**5. Referências cruzadas, uma a uma:**
- Seção 1.2, contribuição 1 → Seções 4.3–4.7: 4.3 ablação (cego, gatilho), 4.4 BC e T_t (Euler × exato no rastreamento via S6), 4.5 mapa de regime, 4.6 atuador/ordem/pontos, 4.7 trocador. Conferem.
- Contribuição 6 → Seção 3.4 (checklist). Confere.
- Introdução → Suplementar S8 (auditoria). Confere.
- Tabela 8:
  - linha "latch": T4 e S2 (mecanismo); S15 linhas ruidosas (SB ≥ 22× a regra, ZN e CC); S12 ("still latches"); S16 ("latch remains"); S13 e S14 (SB pior que nenhum anti-windup); §4.7 e S34 (sem latch).
  - linha "gatilho": T4; S15; S12; S16; S13, S14 (+5 K); T7 (ZN, CC).
  - linha "não universal": T4 e §4.5 (SIMC); S21 (SIMC a 0,05 K); T6 (zona morta, SIMC); S16 (depende do degrau); S13 (SIMC) e S14 (TL em −2 K); T7 (TL).
  - linha "BC^sel": T5; S21–S24; S12; S16 (0,37–1,61); S17; S13, S14; T7 (0,84–1,01).
  - linha "ρ": S11; S25; S10; S10 e S14; §4.7 e S35.
  - linha "ordem": S15 (linhas sem e com ruído; (ii) com folga).
  - Todas existem e dizem o que a célula afirma.

### 9.6 Pendências do usuário

1. **[19]:** volume, número, páginas e DOI conferem no Crossref. Continua pendente conferir os **nomes dos autores no PDF da editora**: o Crossref separa "Inés Tejado Blas" e "M. Vinagre"; o `.bib` usa I. Tejado e B. M. Vinagre (ORCID).
2. **[10] Ziegler e Nichols:** o Crossref dá pp. 759–765 para o artigo; o `.bib` mantém 759–768, que inclui discussão e réplica. Decida qual usar.
3. **Referências sem DOI** (livros e anais antigos, sem DOI confirmado): [5] Åström e Hägglund 2006, [6] Seborg et al. 2010, [9] Bequette 2003, [13] Luyben 2007, [21] Shinskey 1996, [23] Åström e Hägglund 1995. Volume e páginas não faltam em nenhum artigo de periódico.
4. **[31] Zenodo:** DOI placeholder; atribuir no depósito.
5. **Segunda codificação da auditoria:** coluna `second_coder` de `repository/audit_coding.csv` vazia, para o orientador.
6. **Periódico do artigo 1.8** da auditoria: veio do OpenAlex (sem DOI); conferir.
7. **Caixa de 123,6 pt:** do template; só some editando `cas-dc.cls`.

### 9.7 Notas para o orientador

- **Auditoria:** curta, não sistemática, um codificador; 12 artigos lidos de 66 candidatos. Falta uma segunda codificação independente (`audit_coding.csv`, coluna `second_coder`).
- **Segunda planta:** o trocador de calor foi construído para este estudo, não é benchmark publicado; nele o latch não aparece e a heurística ρ não transfere.
- **Sem dados reais:** tudo é simulação; não há dados de planta nem de bancada, nem posição de válvula medida em hardware.
- **Patamar 3 fora de escopo:** compensadores dinâmicos (LMI), controladores com ganho escalonado ou baseados em modelo, e pontos de operação na região instável não foram testados.
- **A conclusão mais frágil** é a equivalência BC × regra direcional: vale sem ruído e se perde com ruído e com stiction (Tabela 8).
- **Decisões do orientador:**
  1. quem faz a segunda codificação da auditoria (e se ela entra antes da submissão);
  2. periódico-alvo (JPC) e o plano B, se o editor achar o escopo estreito;
  3. as pendências de referências da seção 9.6, que exigem acesso ao PDF da editora.
