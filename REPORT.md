# REPORT — Artigo 1 (JPC), v7

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

1. **Nome do script.** Mantive `scripts/jpc_v6_numbers.py`, porque renomear exigiria editar o data statement (regra 2). As tabelas condensadas passaram a `v7_*.tex`, e a lista de macros a `results/jpc/v7_numbers.csv`; `v6_numbers.csv` ficou como base do diff. Resolver quando o data statement entrar no escopo.
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
