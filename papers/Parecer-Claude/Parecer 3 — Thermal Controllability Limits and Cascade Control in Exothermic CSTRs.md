# Parecer 3 — Thermal Controllability Limits and Cascade Control in Exothermic CSTRs

Oct 24, 2026 · @Gabriel

Nota de consenso **67/100** (Qualis A1; periódico assumido: *Journal of Process Control*): revisões maiores.

## Síntese do manuscrito e critérios aplicados

**Tipo:** artigo original (preprint Elsevier, 11 p.) · **Destino:** não indicado no PDF; **premissa adotada: *Journal of Process Control*** (mesmo modelo dos estudos companheiros \[18, 19\]; a régua A1 seria a mesma em *Chemical Engineering Science* ou *CERD*) · **Nível:** Qualis A1.

O manuscrito separa três limites do mesmo CSTR de três estados com jaqueta dinâmica: instabilidade em malha aberta, autoridade do atuador e perda de capacidade de troca térmica. Mostra que, com a alimentação nominal (Tf = 350 K), há um único estado estacionário estável; o *saddle* (345,00 K, λ₁ = +0,7435 min⁻¹) só existe com alimentação resfriada (Tf = 320 K). Deriva a capacidade crítica UAcrit (60,0% no ponto nominal, 40,4% no saddle), analisa a estabilização por SIMC (τc < 0,293 min com ação integral), explica por que uma cascata funciona (sub-bloco A₁₂ estável com a jaqueta regulada) e mostra que a razão de ganhos em malha aberta tem sinal errado no saddle. Contra choque de +10 K no suprimento de coolant a cascata reduz o IAE em 95,3%; sob incrustação guiada pela reação, os laços de ganho fixo perderiam o saddle a UA ≈ 86–89% do valor limpo, bem antes de 40,4%.

**Critérios aplicados.** O JPC aceita aplicações de controle a processos, modelagem e métodos de projeto, mas a página da Elsevier exclui projeto "tradicional" como PID tuning e variantes. Aqui o PI-SIMC é ferramenta e não a contribuição; o núcleo (limites de controlabilidade, saddle, estrutura de cascata) está dentro do escopo, e o trecho de regra de sintonia é a parte vulnerável. Em A1, esperam-se contribuição nova, comparação com a literatura de plantas instáveis, validação sob incerteza e reprodutibilidade.

**Normas conferidas.** Quatro *highlights* de 78–80 caracteres (ok); CRediT presente (único dos três manuscritos); dados em GitHub; ORCID vazio; sem declaração de IA generativa (se aplicável). O *guide for authors* completo não pôde ser aberto; limites de resumo e estilo não foram conferidos na fonte.

**Verificação independente.** Recalculei de forma independente: o estado estacionário e os três equilíbrios (qj entre 36,5 e 80,0 L/min com 3 raízes; o artigo traz 36,3–80,3 pela grade), os autovalores do saddle (+0,7435; −0,9031; −8,2884), τu = 1,345 min, G(0) = 0,4413, K₁ exato = 4,52 e razão −2,367, UAcrit = 60,0% e 40,4%, a fórmula t\_pred, e as fronteiras de UA congelado com os ganhos do artigo: **89,25% (SISO) e 86,15% (cascata)**, idênticas às reportadas. Uma divergência pontual (b₃ em UAcrit) está nos problemas maiores.

## Revisor 1 — Dr(a). em controle de plantas instáveis e controlabilidade · perfil rigoroso

**Avaliação geral.** É o mais sólido dos três manuscritos: a análise é analítica, os números reproduzem e as limitações são declaradas. As falhas estão na interpretação da manchete (fronteira de estabilidade vs perda prática de regulação), no baseline SISO enfraquecido, em uma explicação de mecanismo que o próprio modelo desmente e em recomendações não testadas.

**Problemas maiores**

1. **O mecanismo "perda de ganho do atuador" não é o que causa as fronteiras de 86–89% (Sec. 4.3, 5.2, Fig. 5).** Recalculei Kc·k ao longo de UA congelado: 1,57 em UA = 89,3% (fronteira SISO), 1,49 em 86,1% (cascata) e só cruza 1 perto de UA ≈ 70% (1,05 a 70%; 0,72 a 60%). A condição estática Kc·k > 1 ainda é satisfeita quando o laço perde estabilidade; a perda é dinâmica (par complexo cruzando o eixo), não por falta de ganho estático. Além disso k = −G(0) depende de a₂₃ ∝ UA e de det(−A), não só de b₃. Identificar o mecanismo (tipo de autovalor), mostrar k(UA) e margens de fase/ganho vs UA.
2. **A manchete supera as simulações dinâmicas (Resumo, Highlight 4, Conclusão 5, Tab. 6).** O laço SISO só sai da banda de 5 K em 28,06 min, quando UA/UA₀ ≈ 52% (estimativa quase-estacionária 0,3 + 0,7·e^(−κ r̄ t)); satura em UA ≈ 44,8%, ou seja, ≈ 4 pontos acima de UAcrit = 40,4%. As fronteiras "congeladas" são critérios lineares com taxas de crescimento pequenas (+0,02 min⁻¹ em 86%; +0,06 em 80%; amplificação de 100× leva de ≈ 150 a 460 min para λ entre 0,03 e 0,01). A cascata sai da banda aos 4,06 min (UA ≈ 89%) embora a análise congelada a preveja estável até 86%; a explicação ("most likely... fast decline of UA") é conjectura. Exige-se varrer κ\_foul (10× e 100× menor) e mostrar a convergência para a previsão congelada, reportar taxas de crescimento e reescrever Resumo e Conclusão 5.
3. **Baseline SISO enfraquecido (Sec. 3.1, 5.1; "95,3%").** SIMC com τc = 0,10 min tem abscissa −0,064 min⁻¹ (constante de tempo ≈ 15,6 min), sem D, sem otimização e sem alvo de Ms; o pós-choque tem abscissa +0,055 min⁻¹, uma pequena mudança de ganho poderia estabilizar. O IAE de 497 K·min é dominado por um ciclo-limite acumulado em 58 min e cresce com o horizonte. Comparar com PI/PID otimizado (SISO e cascata) e usar classificação assentou/não assentou e IAE em janela fixa.
4. **Limite fundamental e robustez ausentes (Sec. 3).** Para polo instável p = 0,7435 min⁻¹ e atraso efetivo θ = 0,648 min, ‖S‖∞ ≥ e^(pθ) ≈ 1,62 (limite clássico, ref. \[23\]); o manuscrito já nota θ/τu ≈ 0,48 mas não reporta Ms, margens nem margem de atraso dos laços. Sem ruído, lag de sensor ou incerteza paramétrica, apesar de o saddle ser hipersensível a E/R, k₀ e ΔH. Para A1, é indispensável um Monte Carlo/Sobol como no manuscrito 1.
5. **Contribuições (ii) e (iii).** Kc·k > 1 é a condição estática clássica para estabilizar polo instável (Eq. 14–15 são elementares); a prova "exata só para P" seria Routh–Hurwitz em forma fechada, hoje feita numericamente em seis linhas ("over the tested range"). A "razão de ganhos em malha aberta" G(0)/K₂ é atribuída a \[3, 15, 5\] sem equação ou página; a prática padrão é identificar o mestre com o escravo fechado, exatamente o que o artigo faz depois: sem citação, o "sinal errado" pode ser espantalho. K₂ = −b₃/a₃₃ é o ganho com T fixo, não o ganho de malha aberta do sistema completo. Falta literatura de PI/PID para FOPDT instável (limites de θ/τu, Ti mínimo) e de CSTR cascata/jaqueta.
6. **Recomendação principal não testada (Sec. 5.2, 6).** O *gain scheduling* do escravo em 1/(T̄ⱼ − Tⱼf) é a conclusão prática e não é simulado, embora o modelo esteja disponível. Testar e refazer Tab. 6 e Fig. 5.
7. **Divergência numérica (Sec. 4.3).** O texto dá b₃ = −0,315 K/L em UAcrit e "fator 4,6". Recalculei T̄ⱼ = T̄ − Q\_load/UAcrit = 305,35 K, logo b₃ = −0,268 K/L e fator 5,4. Verificar qual UA foi usado.
8. **Lei de incrustação (Eq. 20, Sec. 4.1).** É assintótica em UA, não na resistência de incrustação (1/U = 1/U₀ + R\_f, Kern–Seaton); as refs. \[11–13\] sustentam deposição ligada a temperatura de parede, não à taxa da reação principal. O κ\_foul comprime dias em dezenas de minutos e os resultados dinâmicos dependem dele (ver item 2).
9. **Domínio de atração (Sec. 5.1).** Um tamanho e um instante de choque (+10 K em T\_jf, +5 K em T\_f). Em planta instável com saturação e taxa a estabilidade não é global; mapear a amplitude máxima tolerada por arquitetura. No choque de T\_f o pico da cascata é pior (24,82 K vs 19,24 K) e o ganho de 42,6% é só em IAE; o mestre com τc₁ = θ₁ não é ajustado. A versão de anti-windup ("conditional integration") não é detalhada, o que é crítico quando o windup pode causar ignição.
10. **Relevância (Sec. 1, 5.3).** O saddle exige modificar o benchmark (T\_f = 320 K) e tem conversão de 41%; as próprias conclusões dizem que o saddle não se transfere ao ponto nominal. Justificar relevância industrial e refletir isso no título e no resumo.
11. **Literatura e sobreposição.** Poucas referências pós-2015; refs. \[18, 19\] "em revisão" não verificáveis; modelo e Tab. 1 coincidem com os estudos companheiros.

**Problemas menores**

- Fig. 2: projeção 3D→2D sem T\_j inicial; usar continuação em vez de grade para a faixa de multiplicidade (o artigo traz 36,3–80,3 L/min; recalculei 36,5–80,0).
- Esclarecer análise contínua vs discreta (ZOH) na Tab. 3; "exact" no Resumo exige a prova do item 5.
- A Eq. (19) é exata por construção (mesmo modelo); testar com descasamento. "upstream of nothing the slave can measure" é obscuro.
- ORCID vazio; sem declaração de IA generativa.

| Critério | Peso | Nota R1 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 58 |
| Aderência ao escopo e relevância | 10% | 58 |
| Revisão da literatura e posicionamento | 10% | 48 |
| Metodologia e rigor | 20% | 66 |
| Resultados e análise | 15% | 68 |
| Discussão e conclusões | 10% | 58 |
| Redação, estrutura e apresentação | 10% | 80 |
| Conformidade com normas e referências | 5% | 78 |
| **Nota global (ponderada)** |  | **63/100** |

## Revisor 2 — Dr(a). em dinâmica e controle de reatores · perfil amigável e construtivo

**Avaliação geral.** Um artigo com ideia forte e boa execução: relacionar o limite termodinâmico de controlabilidade (UAcrit) com a perda de estabilidade de laços SISO e em cascata sob incrustação, para um CSTR com ponto de operação instável. A análise é, em grande parte, analítica e verificável, o que é raro e valioso. Com alguns ajustes de enquadramento (fronteiras lineares versus perda prática de regulação) e testes complementares, o trabalho tem boa chance de atender ao JPC.

**Pontos fortes**

1. **Contribuição conceitual clara.** Unir a fronteira de controlabilidade UAcrit (Eq. 11) à análise de laços com ganho decrescente dá ao leitor um critério físico simples para saber "até onde" a incrustação é tolerável. Recalculei UAcrit = 40,4% e o resultado confere.
2. **Rigor analítico.** As condições de estabilidade (Routh/ganho estático Kc·k > 1) e a estrutura do sub-bloco A₁₂ na cascata são derivadas de forma transparente; a Eq. (21) para o tempo até a saturação (quase-estacionária) é uma ferramenta prática.
3. **Honestidade sobre limitações.** Os autores dizem que o saddle exige T\_f modificado e que não se transfere ao ponto nominal, que a análise congelada é um critério linear e que a conclusão depende da lei de deriva. Isso aumenta a credibilidade.
4. **Boa escolha do caso de estudo.** O ponto de sela em T\_f = 320 K (raiz única do equilíbrio para o cenário reportado, faixa de multiplicidade 36–80 L/min) é um cenário limpo para ilustrar o problema de controlar uma planta instável com atuador limitado em taxa.
5. **Resultado prático interessante.** A cascata amplia a margem frente à incrustação (estabilidade congelada até ≈ 86% de UA contra ≈ 89% do SISO) e reduz o IAE no distúrbio de T\_jf; o princípio de agendar o escravo pela diferença T̄ⱼ − Tⱼf é prático e promissor.
6. **Reprodutibilidade e redação.** Parâmetros tabulados, textos claros e figuras informativas; os números que recalculei (saddle, fronteiras congeladas, k(UA), contagens) batem, com a única exceção de b₃ em UAcrit.

**Sugestões construtivas**

- **Esclarecer o mecanismo da perda de estabilidade.** Mostrar k(UA) e o tipo de autovalor que cruza (par complexo vs real) e margens de fase/ganho em função de UA; assim a explicação "perda de ganho do atuador" é substituída por uma demonstrada, e a figura de fronteiras ganha poder explicativo.
- **Alinhar manchete e dinâmica.** Varrer κ\_foul (10× e 100× menor) e mostrar que a simulação converge para a previsão congelada; reportar taxas de crescimento. Reformular o Resumo e a Conclusão 5 para dizer "fronteira linear de estabilidade" e, separadamente, "perda prática de regulação" (≈ 52% de UA para o SISO).
- **Reforçar o baseline SISO.** Incluir PI/PID otimizado com alvo de Ms e comparar na mesma classificação (assentou/não assentou, IAE em janela fixa). O ganho da cascata, se persistir, ficará muito mais convincente.
- **Testar o *gain scheduling* proposto.** O modelo já está disponível; uma simulação adicional do escravo agendado por 1/(T̄ⱼ − Tⱼf) transforma a recomendação principal em resultado.
- **Acrescentar robustez.** Reportar Ms, margens e margem de atraso; relacionar com o limite Ms ≥ e^(pθ) ≈ 1,62; incluir ruído de medição e um Monte Carlo curto em E/R, k₀ e ΔH, dada a sensibilidade do saddle.
- **Corrigir b₃ em UAcrit** (−0,268 K/L e fator 5,4 pelo meu cálculo, contra −0,315 e 4,6 no texto) ou explicitar o UA usado.
- **Citar e posicionar a "razão de ganhos".** Dar a equação e a página das referências \[3, 15, 5\] ou reformular como observação própria; acrescentar a literatura de PI/PID para FOPDT instável e de cascata em jaqueta de CSTR.
- **Justificar a lei de incrustação** (assintótica em UA vs resistência de Kern–Seaton) e as referências \[11–13\], e explicitar o anti-windup usado ("conditional integration").
- **Relevância e escopo.** Reforçar na Introdução por que o ponto de operação instável importa industrialmente (conversão de 41%, operação de máxima produção) e ajustar o título/resumo ao que foi mostrado; avaliar a aderência ao JPC, já que a sintonia de PID aparece como componente.
- **Detalhes:** continuação em vez de grade na Fig. 2, testes com descasamento na Eq. (19), ORCID, declaração de IA generativa e atualização das refs. "em revisão".

| Critério | Peso | Nota R2 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 72 |
| Aderência ao escopo e relevância | 10% | 68 |
| Revisão da literatura e posicionamento | 10% | 58 |
| Metodologia e rigor | 20% | 76 |
| Resultados e análise | 15% | 78 |
| Discussão e conclusões | 10% | 70 |
| Redação, estrutura e apresentação | 10% | 84 |
| Conformidade com normas e referências | 5% | 80 |
| **Nota global (ponderada)** |  | **73/100** |

## Revisor 3 — Dr(a). em sistemas dinâmicos e metodologia científica · perfil imparcial

**Avaliação geral.** O manuscrito é o mais maduro do conjunto e a análise matemática é sólida. Ponho o problema central onde R1 o pôs: a afirmação de maior destaque (fronteiras de 86–89% de UA) é um critério linear com UA congelado, e as simulações dinamicamente consistentes dizem outra coisa (perda de regulação em ≈ 52% de UA para o SISO). Isso é corrigível com reenquadramento e com a varredura de κ\_foul. Concordo com R2 em que a base analítica e a honestidade justificam uma decisão de revisão maior, não de rejeição.

**Pontos fortes**

- Base analítica transparente (UAcrit, Routh/Kc·k > 1, sub-bloco A₁₂, Eq. 21), verificada por recomputação.
- Limitações declaradas; reconhece que o saddle exige T\_f modificado.
- Caso de estudo claro (planta instável, atuador limitado em taxa) e resultado prático plausível (cascata + agendamento).
- Redação e reprodutibilidade boas; aderência ao JPC melhor que a do manuscrito 1, embora com componente de sintonia.

**Pontos fracos**

- **Mecanismo errado:** Kc·k ≈ 1,5 nas fronteiras; a perda é dialâmica (par complexo), não por falta de ganho estático.
- **Manchete acima da evidência:** fronteira congelada vs perda de regulação em 28 min (UA ≈ 52%); explicação da cascata ("most likely") conjectural; κ\_foul não varrido.
- **Baseline SISO enfraquecido** (SIMC τc = 0,10, sem D, sem otimização) e IAE dependente do horizonte.
- **Robustez ausente:** Ms ≥ e^(pθ) ≈ 1,62, margens, ruído, incerteza paramétrica.
- **Recomendação central não simulada** (agendamento do escravo).
- **Contribuições (ii)–(iii)** elementares ou sem citação; "razão de ganhos" potencialmente espantalho.
- **b₃ em UAcrit** divergente (−0,268 vs −0,315 K/L); lei de incrustação e domínio de atração pouco discutidos.

**Plano de melhoria**

*Indispensável*

1. Varrer κ\_foul (10× e 100× menor); distinguir "fronteira linear" de "perda prática de regulação" e reescrever Resumo, Highlight 4 e Conclusão 5.
2. Identificar o mecanismo (k(UA), tipo de autovalor, margens vs UA) e corrigir a explicação de "perda de ganho".
3. Fortalecer o baseline SISO (PI/PID otimizado com Ms-alvo) e usar métricas por janela fixa.
4. Simular o *gain scheduling* do escravo e refazer Tab. 6 e Fig. 5.
5. Reportar Ms, margens e margem de atraso (limite Ms ≥ 1,62) e incluir um teste de robustez (ruído + Monte Carlo curto em E/R, k₀, ΔH).

*Fortalece*

6. Corrigir b₃ (ou indicar o UA usado); testar a Eq. (19) com descasamento.
7. Fundamentar a "razão de ganhos" (equação e página de \[3, 15, 5\]) e a prova de "exata só para P" (Routh–Hurwitz em forma fechada).
8. Revisar a lei de incrustação (Kern–Seaton) e as refs. \[11–13\]; descrever o anti-windup; mapear a amplitude máxima de choque tolerada por arquitetura.
9. Incluir literatura de PI/PID para FOPDT instável e cascata em jaqueta; atualizar referências pós-2015; substituir as refs. "em revisão".

*Desejável*

10. Justificar a relevância industrial do saddle (T\_f = 320 K, conversão de 41%) no título/resumo.
11. Continuação em vez de grade na Fig. 2; esclarecer contínuo vs ZOH na Tab. 3; ORCID e declaração de IA generativa.

| Critério | Peso | Nota R3 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 64 |
| Aderência ao escopo e relevância | 10% | 62 |
| Revisão da literatura e posicionamento | 10% | 52 |
| Metodologia e rigor | 20% | 70 |
| Resultados e análise | 15% | 72 |
| Discussão e conclusões | 10% | 62 |
| Redação, estrutura e apresentação | 10% | 82 |
| Conformidade com normas e referências | 5% | 78 |
| **Nota global (ponderada)** |  | **67/100** |

## Discussão entre os revisores

**Ponto 1 — Mecanismo da perda de estabilidade.** *R1:* recalculei Kc·k = 1,57 (UA = 89,3%) e 1,49 (86,1%), ainda > 1 quando o laço perde estabilidade; Kc·k só cruza 1 perto de UA ≈ 70%. A perda é dinâmica, não por falta de ganho estático. *R2:* sugere mostrar k(UA), o tipo de autovalor e margens. *R3:* concorda; a explicação "perda de ganho do atuador" não pode permanecer. **Resolução:** unanimidade; exigência obrigatória.

**Ponto 2 — Manchete vs simulação dependente do tempo.** *R1:* o SISO sai da banda de 5 K em 28,06 min (UA ≈ 52%) e satura em ≈ 44,8%, enquanto as fronteiras de 86–89% são critérios lineares congelados com taxas de crescimento pequenas (+0,02 min⁻¹ em 86%); a saída da cascata aos 4,06 min (UA ≈ 89%) é explicada por conjectura. *R2:* o critério congelado é legítimo como resultado analítico, desde que rotulado. *R3:* separar "fronteira linear" de "perda prática de regulação" e varrer κ\_foul. **Resolução:** R1 aceita o resultado como contribuição se for rotulado e se a convergência para a previsão congelada for mostrada.

**Ponto 3 — Baseline SISO.** *R1:* SIMC com τc = 0,10 min, sem D e sem otimização; o pós-choque tem abscissa +0,055 min⁻¹ e o IAE de 497 K·min depende do horizonte (ciclo-limite). *R2:* concorda e sugere PI/PID otimizado. *R3:* o "95,3%" não deve aparecer sem esse controle. **Resolução:** exigência obrigatória.

**Ponto 4 — Robustez e recomendação central.** *R1:* Ms ≥ e^(pθ) ≈ 1,62; o agendamento do escravo não é simulado. *R2:* o modelo já está disponível, é uma simulação adicional. **Resolução:** ambas obrigatórias.

**Ponto 5 — Originalidade.** *R1:* Kc·k > 1 é clássico e a "razão de ganhos" pode ser espantalho sem citação. *R2:* a combinação com UAcrit e a Eq. (21) é nova. **Resolução:** a contribuição é UAcrit + fronteira de controlabilidade + tempo até a saturação; (ii) e (iii) devem ser rebaixadas ou fundamentadas.

**Ponto 6 — Nota e decisão.** R1 (63), R2 (73), R3 (67). Os problemas maiores são corrigíveis com o modelo existente (varredura de κ\_foul, baseline mais forte, agendamento, margens), sem refazer o estudo; a base analítica é sólida. **Resolução:** revisão maior (banda 62–77), nota consenso 67. Registra-se a premissa de que o período-alvo é o JPC, não indicado no manuscrito.

## Consenso, decisão e exigências

| Critério | Peso | R1 | R2 | R3 | Consenso |
| --- | --- | --- | --- | --- | --- |
| Originalidade e contribuição | 20% | 58 | 72 | 64 | 63 |
| Aderência ao escopo e relevância | 10% | 58 | 68 | 62 | 62 |
| Revisão da literatura e posicionamento | 10% | 48 | 58 | 52 | 51 |
| Metodologia e rigor | 20% | 66 | 76 | 70 | 70 |
| Resultados e análise | 15% | 68 | 78 | 72 | 72 |
| Discussão e conclusões | 10% | 58 | 70 | 62 | 62 |
| Redação, estrutura e apresentação | 10% | 80 | 84 | 82 | 82 |
| Conformidade com normas e referências | 5% | 78 | 80 | 78 | 78 |
| **Nota global (ponderada)** |  | **63** | **73** | **67** | **67/100** |

**Decisão (Qualis A1, Journal of Process Control — período assumido, não indicado no manuscrito): revisão maior (banda 62–77).** A base analítica é sólida e as lacunas são corrigíveis com o modelo existente.

**Exigências obrigatórias**

1. Varrer κ\_foul (10× e 100× menor), distinguir "fronteira linear de estabilidade" de "perda prática de regulação" (≈ 52% de UA para o SISO) e reescrever Resumo, Highlight 4 e Conclusão 5.
2. Identificar o mecanismo (k(UA), tipo de autovalor, margens vs UA) e corrigir a explicação de "perda de ganho do atuador".
3. Fortalecer o baseline SISO (PI/PID otimizado com Ms-alvo; métricas por janela fixa) antes de reportar o ganho da cascata.
4. Simular o *gain scheduling* do escravo e refazer Tab. 6 e Fig. 5.
5. Reportar Ms, margens e margem de atraso (limite Ms ≥ 1,62) e incluir ruído e um Monte Carlo curto em E/R, k₀, ΔH.
6. Corrigir b₃ em UAcrit (−0,268 K/L e fator 5,4 pelo cálculo dos revisores) ou indicar o UA usado.

**Exigências recomendadas**

7. Fundamentar a "razão de ganhos" (equação e página de \[3, 15, 5\]) e a prova de "exata só para P"; rebaixar as contribuições (ii)–(iii) se elementares.
8. Revisar a lei de incrustação (Kern–Seaton) e as refs. \[11–13\]; descrever o anti-windup; mapear a amplitude máxima de choque por arquitetura.
9. Literatura de PI/PID para FOPDT instável e de cascata em jaqueta; atualizar referências pós-2015; substituir as refs. "em revisão".
10. Justificar a relevância do saddle (T\_f = 320 K, conversão 41%) e esclarecer o escopo frente ao JPC; confirmar o período-alvo.
11. Continuação na Fig. 2; contínuo vs ZOH na Tab. 3; ORCID, CRediT e declaração de uso de IA generativa.

**Conclusão da revisão por pares**

O manuscrito deriva o limite termodinâmico de controlabilidade (UAcrit) de um CSTR exotérmico com ponto de operação instável e o relaciona à perda de estabilidade de laços SISO e em cascata sob incrustação, propondo o agendamento do escravo. A análise é majoritariamente analítica, transparente e verificável (o saddle, as fronteiras congeladas e UAcrit = 40,4% foram reproduzidos), e as limitações são declaradas com honestidade. As principais reservas são: a manchete (estabilidade até 86–89% de UA) é um critério linear congelado, enquanto as simulações dependentes do tempo indicam perda de regulação em torno de 52%; o mecanismo "perda de ganho do atuador" não se sustenta (Kc·k permanece em ≈ 1,5 nas fronteiras); o baseline SISO é enfraquecido; a robustez e a recomendação central (agendamento) não foram testadas; e há uma divergência numérica em b₃. Recomenda-se revisão maior: as lacunas são corrigíveis com o modelo existente, e o resultado, uma vez reenquadrado e complementado, tem potencial para uma contribuição sólida.
