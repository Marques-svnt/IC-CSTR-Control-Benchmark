# Parecer 2 — When Does Nonlinear Model Predictive Control Outperform Robust PID?

Oct 24, 2026 · @Gabriel

Nota de consenso **60/100** para o *Computers & Chemical Engineering* (Qualis A1): rejeitar e encorajar nova submissão.

## Síntese do manuscrito e critérios aplicados

**Tipo:** artigo original (preprint Elsevier, 11 p.) · **Destino:** *Computers & Chemical Engineering* (CCE) · **Nível:** Qualis A1.

O manuscrito compara um NMPC (CasADi/IPOPT, modelo RK4, N = 50 amostras = 1,0 min, Δt = 0,02 min) com duas sintonias robustas de PID (AMIGO e ITAE ótimo com Ms ≤ 1,6) no mesmo CSTR com válvula limitada em amplitude e taxa e anti-windup direcional. O NMPC é avaliado com estado verdadeiro ("Oracle") e com estimador EKF + horizonte móvel que reconstrói CA e o fator de incrustação αUA a partir de dois termopares (NMPC-MHE). Em seis cenários, reporta: ganho de apenas 2,3% no IAE servo nominal; redução de 21,0% (vs AMIGO) e 25,2% (vs ITAE ótimo) após perda abrupta de troca térmica a 70%; *offset* de +8,7/+8,9 K sob choques de alimentação não medidos, que ambos os PIDs rejeitam; nenhuma lei alcança o setpoint a 60% de UA; e custo de 31–39 ms por amostra contra 0,09 ms. Resume cinco critérios sobre quando a predição não linear compensa.

**Critérios aplicados.** O periódico não é nomeado no PDF; o Parecer 3 cita este trabalho como *Computers & Chemical Engineering* (em revisão), e usei essa premissa. O escopo, segundo a descrição pública do CCE, é a aplicação de computação e tecnologia de sistemas a problemas de engenharia química, incluindo explicitamente dinâmica, controle e monitoramento de processos e comparação de metodologias: a aderência é boa. Em A1 esperam-se baseline justo e forte, validação sob incertezas, análise de generalidade e reprodutibilidade.

**Normas conferidas.** Quatro *highlights* de 69–77 caracteres (ok); disponibilidade de dados com GitHub. Faltam declaração CRediT e declaração de IA generativa (se aplicável); ORCID vazio. O *guide for authors* completo do CCE não pôde ser aberto (acesso automatizado bloqueado); limites de resumo e estilo não foram conferidos na fonte.

**Verificação independente.** Recalculei as razões percentuais citadas (2,3%; 21,0%; 25,2%; 10,4%; +1,7%; 39% a mais de curso; 24% a menos de curso) e todas conferem com as tabelas. Recalculei também o limite termodinâmico para o setpoint usado aqui: a capacidade crítica de UA é **63,8%** em T = 394,65 K (contra 60,0% em 396,65 K), e o equilíbrio com válvula aberta (300 L/min) e UA = 60% fica em 396,65 K, acima do setpoint. Isso reenquadra o cenário de 60% (ver Revisor 1).

## Revisor 1 — Dr(a). em NMPC e estimação de estados · perfil rigoroso

**Avaliação geral.** A pergunta do título é boa e o desenho experimental tem méritos (mesma válvula, anti-windup justo, estimador realista). Mas o NMPC avaliado é deficiente por construção em regulação, o ganho atribuído à "predição não linear" está confundido com adaptação e planejamento sob restrição, o PID de comparação é escolhido de modo incompleto e o NMPC nunca enfrenta erro de modelo. As "cinco regras" generalizam além do que um reator e um desenho permitem.

**Problemas maiores**

1. **NMPC sem ação integral/modelo de perturbação (Sec. 4.6, 5, Tab. 5).** O *offset* de +8,7/+8,9 K é consequência conhecida (as refs. \[22, 23\] são citadas pelos autores) e a formulação *offset-free* é prática padrão. O resultado não responde ao título: compara PID bom com NMPC incompleto. A explicação do item 1 da Sec. 4.6 ("o modelo nominal já alcança T\_sp com a entrada atual") não é consistente com o modelo: o equilíbrio nominal em ≈166 L/min está bem abaixo de T\_sp (o nominal precisa de ≈111 L/min). Mais provável é o efeito de horizonte curto com promessa perpétua; falta diagnóstico (trajetória prevista × realizada, varredura de N). Exige-se a versão *offset-free* (perturbação na saída ou no balanço de T, com αUA) e a repetição do cenário.
2. **Confusão entre três fatores (Sec. 4.3, 4.9, Conclusão 2).** O NMPC (a) adapta αUA, (b) planeja a rampa contra a taxa da válvula e (c) usa o modelo não linear; os PIDs são fixos e sintonizados na planta nominal. O ganho de 21% não pode ser atribuído à "predição não linear". Faltam: NMPC com αUA congelado; MPC linear adaptativo; PID com *gain scheduling* em αUA estimado (o manuscrito 3 sugere o agendamento como passo natural); PID reotimizado para o cenário.
3. **Seleção do "melhor PID" (Sec. 3.2, 4.1).** AMIGO é declarado o mais rápido na recuperação do evento da Sec. 4.3 (escolha feita com o próprio resultado, circular) e a ref. \[21\] não traz cenário de incrustação. Segundo \[21\] (Tab. 5), ZN e CC (|Kp|/Ti ≈ 238 e 234 min⁻¹ contra 54 do AMIGO) são os melhores reguladores, e com anti-windup correto são estáveis. Sem testar ZN, CC, TL, SIMC e um PID otimizado nesse cenário, "21,0% abaixo do melhor PID" não está estabelecido.
4. **NMPC no melhor caso: sem erro de modelo (Sec. 2.3, 4.9).** Planta e NMPC compartilham estrutura e, ao que tudo indica, o integrador RK4 ("o MHE reproduz o Oracle exatamente"). Só αUA difere. Não há erro em E\_a/R, k₀, ΔH, T\_f, C\_Af, que o manuscrito 1 mostra serem determinantes. Exige-se integrador independente e preciso na planta e Monte Carlo/Sobol de incertezas para as duas classes.
5. **Curso de válvula confundido por ruído (Tab. 2, 7, Conclusão 2).** O Oracle é sem ruído; os PIDs, com σ = 0,05 K sem filtro, já operam perto do teto de TV (≈ 800 L/min; 727 a 0,1 K, Tab. 6). "Menos da metade do curso" (252,4 vs 672,1/694,4) e "quatro vezes menos" no rastreamento amplo (388,7 vs 1596,7/1650,2) comparam ruído com ausência de ruído. A comparação justa é com o NMPC-MHE: 571,0 (15–18% menos) e 1221,0 (24% menos). Falta um PID com filtro de medição ou Kalman + PID.
6. **Realismo dos cenários (Sec. 4.3, 4.5).** A perda de 30% de UA em uma amostra favorece quem tem estimador; incrustação real é lenta (o manuscrito 3 tem lei de deriva). A varredura da Sec. 4.5 aplica UA reduzido desde t = 0 com o degrau, o que não é incrustação. A vantagem sobre o ITAE ótimo é 8,7% (90%), 8,3% (80%) e 10,4% (70%): "cresce com o descasamento" é fracamente sustentado. A 60% de UA o setpoint (394,65 K) é inviável *em regime*: calculei UAcrit = 63,8% para esse T e o equilíbrio com válvula aberta a UA = 60% é 396,65 K. O cenário não testa controladores, e a descrição "não alcança em 10 min" subestima o fato. A Conclusão 5 deve usar o UAcrit correto.
7. **Horizonte e relatório do solver (Sec. 2.2, 4.3).** N = 50 (1,0 min) permite mover a válvula no máximo 80 L/min, contra curso total em 3,75 min e ≈ 110 L/min de variação no evento; sem custo/restrição terminal. O teste N = 75 é no degrau nominal (mudança líquida de 10,9 L/min), não representativo. Sem taxa de falha do IPOPT, iterações, pior tempo, aquecimento ou hardware; 31–39 ms são médias que incluem a integração da planta e o PID (0,09 ms) é quase só integração: a razão subestima o custo do controlador.
8. **Estatística e coerência (Tab. 6–7, Sec. 4.7).** Das 600 simulações, 240 são determinísticas (Oracle em todos os σ e linhas σ = 0); 360 estocásticas; sem IC nem testes pareados. Na Tab. 7 o NMPC-MHE (19,66) supera o "Oracle" (19,98), o que contradiz o Oracle como cota e não é explicado. R\_e fica fixo (0,05 K²) enquanto σ chega a 1 K; "R\_e = 0,05 K² é maior que σ = 0,05 K" compara variância com desvio-padrão.
9. **Estimador (Sec. 2.3, 4.4).** Pesos 4 e 1/4 do MHE (Eq. 7) arbitrários, não derivados das covariâncias, apesar de "escalas físicas"; Q\_α não tem efeito (Tab. 3), logo a afirmação de que o passeio aleatório segue a perda abrupta não descreve o mecanismo real; posto 4 não mede condicionamento (reportar valores singulares). Sob choques de alimentação αUA absorve a perturbação (0,981/0,985): falso alarme que deveria motivar um estimador com perturbação aditiva.
10. **Generalidade e literatura (Sec. 1, 4.9, 5).** Um reator, uma válvula, uma magnitude de incrustação; "cinco critérios" são achados de cenário único apresentados como regras. "Comparações raramente respondem a esta pergunta" sem citação concreta; literatura recente de NMPC/MHE/RL em CSTR (2018–2026) ausente; ref. \[19\] é de 1995.
11. **Sobreposição com o manuscrito 1 (\[21\]).** Linhas da Tab. 1, da Tab. 5 e da Tab. 6 (AMIGO e ITAE ótimo) coincidem numericamente com as Tab. 2, 5 e 7 de \[21\]. É preciso declarar o reuso e a parte nova, e prever a verificação de similaridade.

**Problemas menores**

- "Oracle" é enganoso porque αUA é estimado; renomear.
- Definir Mp e t\_s; unidades de ITAE; legendas das Fig. 2 e 3 pequenas.
- Sem CRediT; ORCID vazio; sem declaração de IA generativa.
- Esclarecer "4% do intervalo de 1,2 s" (39,28/1200 = 3,3%).

| Critério | Peso | Nota R1 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 50 |
| Aderência ao escopo e relevância | 10% | 80 |
| Revisão da literatura e posicionamento | 10% | 48 |
| Metodologia e rigor | 20% | 48 |
| Resultados e análise | 15% | 58 |
| Discussão e conclusões | 10% | 52 |
| Redação, estrutura e apresentação | 10% | 80 |
| Conformidade com normas e referências | 5% | 68 |
| **Nota global (ponderada)** |  | **58/100** |

## Revisor 2 — Dr(a). em controle preditivo aplicado a processos · perfil amigável e construtivo

**Avaliação geral.** O manuscrito faz uma pergunta honesta e relevante, "quando o NMPC compensa frente a um PID bem sintonizado?", e a responde com um desenho experimental cuidadoso: mesma válvula, anti-windup justo para os PIDs, estimador realista em vez de estados perfeitos. O valor está nos critérios práticos finais. Para chegar ao nível A1 faltam o controle de comparação mais justo (NMPC *offset-free*, PID adaptado) e a exposição do NMPC a erro de modelo.

**Pontos fortes**

1. **Pergunta bem formulada e útil.** Em vez de proclamar a superioridade do NMPC, o texto procura as condições em que ele compensa, e entrega cinco critérios que um engenheiro pode levar para a decisão de projeto. Esse tom equilibrado é raro em artigos de NMPC.
2. **Comparação com o mesmo atuador.** Todos os controladores enxergam a mesma válvula limitada em amplitude e taxa, e os PIDs usam o anti-windup direcional. Isso evita o erro clássico de comparar um MPC "com restrições" com um PID "sem restrições".
3. **Estimação de estados tratada a sério.** EKF, MHE e a variante Oracle são comparados; a observação de que Q\_α quase não importa e de que choques de alimentação são absorvidos por αUA é uma contribuição prática, mesmo incompleta.
4. **Cenário de incrustação bem motivado.** A perda de UA é um fenômeno real em reatores, e o texto o conecta à controlabilidade (UAcrit), o que dá substância física ao estudo.
5. **Resultados quantitativos concretos.** Redução de 21% no ITAE frente ao melhor PID, e de 15–24% do curso da válvula no confronto com o NMPC-MHE; as tabelas permitem verificar os números, e os que recalculei (equilíbrios, UAcrit = 63,8%) conferem.
6. **Transparência.** Os autores relatam o *offset* do NMPC em regulação em vez de escondê-lo, e discutem tempos de cálculo (31–39 ms), o que é essencial para o leitor industrial.

**Sugestões construtivas**

- **Adicionar a versão *offset-free* do NMPC** (perturbação na saída ou no balanço de energia, com αUA). É a mudança de maior retorno: remove o *offset* de ≈ 8,8 K, torna a comparação justa em regulação e, provavelmente, melhora ainda mais o desempenho no cenário de incrustação.
- **Separar os ganhos do NMPC.** Rodar NMPC com αUA congelado, um MPC linear adaptativo e um PID com *gain scheduling* por αUA estimado. Assim o texto pode dizer, com base em evidência, qual parcela vem da predição não linear, qual da adaptação e qual do planejamento sob restrição.
- **Selecionar o PID de comparação antes do cenário.** Escolher por critério prévio (p.ex. melhor ITAE na regulação nominal) ou testar todas as regras no evento de incrustação, em vez de eleger o AMIGO com base no próprio resultado.
- **Incluir erro de modelo.** Integrador independente e preciso na planta, e incertezas em E\_a/R, k₀, ΔH, T\_f e C\_Af; um Monte Carlo curto bastaria para mostrar se a vantagem sobrevive. Esta é a lacuna que mais pesa na credibilidade industrial.
- **Ruído de forma simétrica.** Comparar o NMPC-MHE com PID + filtro de medição (ou PID + Kalman) e reportar a taxa de TV por variância de ruído; as frases "metade do curso" e "quatro vezes menos" ficam então justas.
- **Perda gradual de UA** (lei de deriva, como no manuscrito sobre controlabilidade) além do degrau de 30%, e remover o cenário de UA = 60% da lista de testes de controladores, ou mantê-lo como caso inviável *em regime* com UAcrit (63,8%) explícito.
- **Reportar o solver:** falhas do IPOPT, iterações, pior tempo e hardware, separando o custo do controlador do da integração da planta.
- **Estatística:** intervalos de confiança, testes pareados e esclarecimento de por que o NMPC-MHE (19,66) fica melhor que o "Oracle" (19,98) na Tab. 7; renomear "Oracle" para algo como "NMPC com planta sem ruído".
- **Declarar a sobreposição** com o estudo de benchmark de PID (\[21\]) e acrescentar literatura recente (2018–2026) de NMPC/MHE em CSTR, além de CRediT, ORCID e declaração de IA generativa.

| Critério | Peso | Nota R2 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 65 |
| Aderência ao escopo e relevância | 10% | 85 |
| Revisão da literatura e posicionamento | 10% | 58 |
| Metodologia e rigor | 20% | 62 |
| Resultados e análise | 15% | 70 |
| Discussão e conclusões | 10% | 66 |
| Redação, estrutura e apresentação | 10% | 85 |
| Conformidade com normas e referências | 5% | 72 |
| **Nota global (ponderada)** |  | **69/100** |

## Revisor 3 — Dr(a). em sistemas dinâmicos e metodologia científica · perfil imparcial

**Avaliação geral.** O escopo se encaixa bem no CCE e a pergunta é boa. O desenho experimental tem méritos reais, mas a conclusão "NMPC vence o PID em 21%" depende de três escolhas que o próprio texto não controla: um NMPC sem integrador, um PID escolhido a posteriori e uma planta sem erro de modelo. Considero R1 correto no peso dado a esses três pontos e R2 correto ao valorizar o desenho e os critérios práticos.

**Pontos fortes**

- Mesma válvula para todos, PID com anti-windup justo, estimador realista (EKF/MHE).
- Pergunta formulada como "quando" e não "se"; critérios finais práticos.
- Números que recalculei conferem: UAcrit = 63,8% e equilíbrio com válvula aberta a UA = 60% (396,65 K).
- Relato transparente do *offset* e dos tempos de cálculo (31–39 ms).
- Redação e estrutura muito boas, no escopo do CCE.

**Pontos fracos**

- **NMPC sem ação integral/modelo de perturbação** e explicação do *offset* inconsistente com o modelo (equilíbrio nominal ≈ 111 L/min contra ≈ 166 L/min).
- **Três fatores confundidos** (adaptação de αUA, planejamento sob restrição, não linearidade) atribuídos à predição não linear.
- **Seleção circular do melhor PID** (AMIGO eleito pelo cenário de teste).
- **Comparação de curso de válvula confundida por ruído** (PID com ruído e sem filtro vs Oracle sem ruído); a comparação justa mostra 15–24%.
- **Nenhum erro de modelo**; planta e controlador compartilham estrutura e provavelmente o integrador.
- **Cenário de UA = 60% inviável em regime** usado como teste; N = 50 e testes de N no degrau nominal; estatística sem IC; Oracle < NMPC-MHE inexplicado.
- **Sobreposição não declarada** com o benchmark de PID (\[21\]).

**Plano de melhoria**

*Indispensável*

1. NMPC *offset-free* e repetição da regulação, com diagnóstico do *offset* (trajetória prevista vs realizada; varredura de N).
2. Separar as contribuições: NMPC com αUA congelado, MPC linear adaptativo, PID com *gain scheduling* por αUA estimado, PID reotimizado.
3. Seleção do PID por critério prévio ou teste de todas as regras no cenário de incrustação.
4. Erro de modelo (integrador independente; incertezas em E\_a/R, k₀, ΔH, T\_f, C\_Af), com Monte Carlo curto.
5. Comparação de ruído simétrica (PID com filtro/Kalman) e reescrita de "metade" e "quatro vezes"; corrigir a Conclusão 5 com UAcrit = 63,8%.

*Fortalece*

6. Incrustação gradual (lei de deriva) e remoção do caso inviável da lista de testes.
7. Relatório do solver (falhas, iterações, pior tempo, hardware) e custo isolado do controlador.
8. IC e testes pareados; explicar Oracle < NMPC-MHE; R\_e vs σ (variância vs desvio-padrão).
9. Declarar a sobreposição com \[21\] e atualizar a literatura 2018–2026.

*Desejável*

10. Pesos do MHE derivados das covariâncias; valores singulares no lugar do posto.
11. Renomear "Oracle", definir Mp/t\_s, CRediT, ORCID, declaração de IA generativa.

| Critério | Peso | Nota R3 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 54 |
| Aderência ao escopo e relevância | 10% | 82 |
| Revisão da literatura e posicionamento | 10% | 52 |
| Metodologia e rigor | 20% | 54 |
| Resultados e análise | 15% | 62 |
| Discussão e conclusões | 10% | 58 |
| Redação, estrutura e apresentação | 10% | 82 |
| Conformidade com normas e referências | 5% | 70 |
| **Nota global (ponderada)** |  | **62/100** |

## Discussão entre os revisores

**Ponto 1 — NMPC sem ação integral.** *R1:* o *offset* de ≈ 8,8 K é conhecido e a formulação *offset-free* é padrão; compara-se um PID bom com um NMPC incompleto. *R2:* os autores são honestos ao relatar o *offset*. *R3:* a honestidade não substitui o teste; além disso a explicação do texto não é consistente com o modelo (equilíbrio nominal ≈ 111 L/min vs ≈ 166 L/min). **Resolução:** NMPC *offset-free* e diagnóstico do *offset* (trajetória prevista, varredura de N) são exigência obrigatória.

**Ponto 2 — Origem do ganho de 21%.** *R1:* adaptação de αUA, planejamento sob restrição e não linearidade estão misturados; PIDs fixos e sintonizados no nominal. *R2:* propõe separar os fatores (NMPC com αUA congelado, MPC linear adaptativo, PID agendado). *R3:* concorda e lembra que o manuscrito companheiro já sugere o agendamento. **Resolução:** unanimidade; a Conclusão 2 só pode atribuir o ganho à "predição não linear" após esses controles.

**Ponto 3 — Escolha do PID e ruído.** *R1:* o AMIGO foi eleito pelo próprio evento de teste, e "metade"/"quatro vezes" comparam ruído com ausência de ruído. *R2:* sugere critério prévio e PID com filtro. *R3:* a comparação justa com o NMPC-MHE já está nos dados (15–24%), o que é um resultado válido, apenas menor. **Resolução:** reescrever as afirmações com os números justos e refazer a comparação com PID filtrado/Kalman.

**Ponto 4 — Erro de modelo.** *R1:* a planta e o NMPC compartilham estrutura e provavelmente o integrador; sem incertezas em E\_a/R, k₀, ΔH etc. *R2:* concorda que é a lacuna que mais pesa na credibilidade industrial. *R3:* um Monte Carlo curto basta. **Resolução:** exigência obrigatória.

**Ponto 5 — Cenários de incrustação.** *R1:* a 60% de UA o setpoint é inviável em regime (UAcrit = 63,8%; equilíbrio aberto 396,65 K). *R2:* sugere lei de deriva gradual. **Resolução:** corrigir a Conclusão 5 e retirar o caso inviável dos testes de controladores.

**Ponto 6 — Nota e decisão.** R1 (58) e R2 (69) divergem em 11 pontos; R3 (62) fica no meio. O escopo (82) e a redação (82) são fortes, mas metodologia (52) e literatura (52) puxam a nota para baixo. **Resolução:** como o NMPC *offset-free*, o PID de comparação, o erro de modelo e o ruído simétrico refazem a comparação central, a decisão é rejeição com incentivo à resubmissão, com tom encorajador. R2 aceita, registrando que a pergunta e o desenho justificam a resubmissão.

## Consenso, decisão e exigências

| Critério | Peso | R1 | R2 | R3 | Consenso |
| --- | --- | --- | --- | --- | --- |
| Originalidade e contribuição | 20% | 50 | 65 | 54 | 54 |
| Aderência ao escopo e relevância | 10% | 80 | 85 | 82 | 82 |
| Revisão da literatura e posicionamento | 10% | 48 | 58 | 52 | 52 |
| Metodologia e rigor | 20% | 48 | 62 | 54 | 50 |
| Resultados e análise | 15% | 58 | 70 | 62 | 60 |
| Discussão e conclusões | 10% | 52 | 66 | 58 | 54 |
| Redação, estrutura e apresentação | 10% | 80 | 85 | 82 | 82 |
| Conformidade com normas e referências | 5% | 68 | 72 | 70 | 70 |
| **Nota global (ponderada)** |  | **58** | **69** | **62** | **60/100** |

**Decisão (Qualis A1, Computers & Chemical Engineering): rejeição com incentivo à resubmissão (banda 45–61).** Escopo e redação são adequados; o que falta é o controle experimental que sustente a pergunta do título.

**Exigências obrigatórias**

1. NMPC *offset-free* (perturbação na saída ou no balanço de energia, com αUA), repetição da regulação e diagnóstico do *offset* (trajetória prevista vs realizada; varredura de N).
2. Separar as contribuições: NMPC com αUA congelado, MPC linear adaptativo, PID com *gain scheduling* por αUA estimado, PID reotimizado.
3. Selecionar o PID de comparação por critério prévio ou testar todas as regras no cenário de incrustação.
4. Incluir erro de modelo (integrador independente e incertezas em E\_a/R, k₀, ΔH, T\_f, C\_Af) com Monte Carlo.
5. Comparação de ruído simétrica (PID com filtro ou Kalman) e reescrita de "metade do curso" e "quatro vezes"; corrigir a Conclusão 5 com UAcrit = 63,8%.

**Exigências recomendadas**

6. Incrustação gradual (lei de deriva) e retirada do caso inviável (UA = 60%) da lista de testes.
7. Relatório do solver: falhas do IPOPT, iterações, pior tempo, hardware, custo isolado do controlador.
8. IC, testes pareados e explicação de Oracle < NMPC-MHE; corrigir R\_e vs σ; renomear "Oracle".
9. Declarar a sobreposição com o benchmark de PID (\[21\]); literatura de NMPC/MHE em CSTR (2018–2026).
10. CRediT, ORCID e declaração de uso de IA generativa; verificar o limite de resumo e o estilo de referências no guia do CCE, que não pôde ser aberto na fonte.

**Conclusão da revisão por pares**

O manuscrito compara NMPC (com EKF/MHE) e PIDs sintonizados em um CSTR exotérmico com válvula limitada em amplitude e taxa, e identifica cinco critérios para decidir quando o NMPC compensa. A pergunta é relevante, o escopo é adequado ao Computers & Chemical Engineering, o desenho (mesma válvula, anti-windup justo, estimador realista) é cuidadoso, e os valores de equilíbrio e UAcrit puderam ser reproduzidos. Entretanto, a conclusão principal (vantagem de 21% do NMPC) não está estabelecida: o NMPC avaliado não tem ação integral, o ganho confunde adaptação de UA, planejamento sob restrição e predição não linear, o PID de referência foi escolhido a partir do próprio cenário de teste, o curso da válvula compara PID ruidoso com NMPC sem ruído, e o NMPC nunca enfrenta erro de modelo. Recomenda-se a rejeição nesta forma, com forte incentivo à resubmissão: o trabalho tem potencial, desde que as comparações acima sejam refeitas de modo a responder, com evidência, à pergunta do título.
