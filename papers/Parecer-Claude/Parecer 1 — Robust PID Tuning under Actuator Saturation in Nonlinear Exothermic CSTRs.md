# Parecer 1 — Robust PID Tuning under Actuator Saturation in Nonlinear Exothermic CSTRs

Oct 24, 2026 · @Gabriel

Nota de consenso **58/100** para o *Journal of Process Control* (Qualis A1): rejeitar e encorajar nova submissão.

## Síntese do manuscrito e critérios aplicados

**Tipo:** artigo original (preprint Elsevier, 12 p.) · **Destino:** *Journal of Process Control* (JPC, IFAC) · **Nível:** Qualis A1.

O manuscrito compara oito sintonias de PID (Ziegler–Nichols, Cohen–Coon, Tyreus–Luyben, AMIGO e sua versão 2-DOF, SIMC, e otimização ITAE multi-start com Ms ≤ 1,6 e sua versão 2-DOF) em um CSTR exotérmico de três estados com válvula limitada em amplitude \[0, 300\] L/min e em taxa (80 L/min²). Propõe uma regra de *clamping* direcional que congela o integrador quando o comando anterior foi cortado por amplitude ou por taxa (Eq. 13) e a compara, por ablação, com a regra "ingênua" só de amplitude e cega ao sinal (Tab. 3). Complementa com margens de robustez no modelo FOPTD e na planta linearizada (Tab. 4), perturbações de carga (Tab. 5), varredura de τc do SIMC e frente de Pareto (Tab. 6), 1200 simulações com ruído (Tab. 7) e índices de Sobol (Tab. 8). Conclui que a implementação do anti-windup decide o veredicto sobre ZN/CC (IAE 0,940 → 104,123 K·min), que a robustez e não a estabilidade separa as regras, e que a variância do erro é governada por física (alimentação e troca térmica).

**Critérios aplicados.** O JPC cobre aplicação de teoria de controle a problemas de processo, com métodos de projeto como tópico. Verifiquei na página da Elsevier que os métodos avançados de projeto **excluem "técnicas tradicionais de projeto bem estabelecidas e amplamente estudadas, como PID tuning e suas variantes"**. Esse é o risco de escopo central deste manuscrito. Em A1, esperam-se contribuição nova e generalizável, comparação com o estado da arte recente, validação com análise de incerteza e reprodutibilidade.

**Normas conferidas.** Quatro *highlights* de 75–79 caracteres (dentro do limite usual de 85); declaração de disponibilidade de dados com repositório GitHub (sem DOI de arquivamento). Não encontrei declaração CRediT (presente só no manuscrito 3), o campo ORCID está vazio e não há declaração de uso de IA generativa (exigida pela Elsevier quando aplicável). O *guide for authors* completo não pôde ser aberto (acesso automatizado bloqueado), portanto limites de resumo e estilo de referências não foram conferidos na fonte.

**Verificação numérica independente.** Recalculei o estado estacionário, a Jacobiana, os autovalores (−1,5712; −11,8006; −13,2693 min⁻¹), os ganhos das regras ZN/CC/TL/AMIGO/SIMC a partir do FOPTD e os picos Ms. Todos reproduzem as Tabelas 2 e 4: Ms(FOPTD) = 4,14; 4,54; 2,32; 1,45; 1,13; 1,60 e Ms(linear com ZOH) = 1,57; 1,75; 1,15; 1,26; 1,11; 1,30–1,31. A integridade numérica do trabalho é boa; as críticas abaixo são de desenho e de interpretação.

## Revisor 1 — Dr(a). em controle de processos e anti-windup · perfil rigoroso

**Avaliação geral.** O trabalho é numericamente íntegro e bem organizado, mas a mensagem central ("a implementação, não a regra, decide") repousa em uma ablação fraca, e várias conclusões são atribuídas a mecanismos que o próprio manuscrito contradiz em outro ponto. Para um A1, a contribuição metodológica é estreita e o escopo é problemático no JPC.

**Problemas maiores**

1. **Escopo (Sec. 1, Highlights).** O JPC exclui PID tuning e suas variantes dos métodos de projeto. O manuscrito é, na essência, um benchmark de sintonias de PID. É preciso reposicionar a contribuição (metodologia de benchmark com atuador realista) ou escolher outro periódico.
2. **Ablação do anti-windup é um espantalho e confunde três fatores (Sec. 3.2, 4.3, Tab. 3).** A regra "ingênua" nunca dispara para Kp < 0, como os próprios autores escrevem; na prática é *nenhum* anti-windup. Faltam: (a) a condição sem anti-windup; (b) *back-calculation*/tracking, o método padrão da referência \[1\]; (c) uma ablação 2×2 (amplitude × taxa × sinal) para sustentar os "dois mecanismos" da Sec. 4.3, que só são testados juntos. O "842,5%" idêntico para ZN e CC corresponde a T ≈ 377,8 K; recalculei o equilíbrio com válvula 100% aberta (300 L/min, UA nominal) em 377,9 K: o laço satura o resfriamento e fica preso. Isso é a ausência de anti-windup, não uma falha da regra empírica. A Introdução afirma que a literatura atribui a falha à regra, mas não cita nenhum estudo específico (as refs. \[12, 13\] são livros-texto).
3. **Originalidade do clamping direcional (Eq. 13).** É conditional integration sensível ao sinal, com resíduo do passo anterior. Falta delimitar o que é novo frente a clamping padrão e a esquemas com limite de taxa (p.ex. a revisão de Galeani, Tarbouriech, Turner e Zaccarian, *Eur. J. Control*, 2009, e Åström & Rundqwist, 1989).
4. **Ms do FOPTD é artefato; a explicação do ruído está mal atribuída (Sec. 4.4 vs 4.7, Fig. 2).** Na planta linearizada exata, ZN tem Ms = 1,57 (já abaixo de 1,6) e CC 1,75 (Tab. 4). A Sec. 4.4 reconhece que os picos de alta frequência do FOPTD vêm do atraso aparente; a Sec. 4.7 usa esses mesmos picos para explicar o ruído. O que governa o ruído é o ganho de alta frequência: recalculei |Kp|(1+N) = 490 (ZN), 559 (CC), 77 (SIMC) L/min por K. A conclusão 2 ("robustez, não estabilidade") deve ser reescrita em termos de ‖CS‖∞ na planta exata. Também, o delay-free Ms que "retorna valores próximos de 1 para quase qualquer ganho" (Sec. 3.4, item 7) é 1,37 (ZN) e 1,50 (CC) pelo meu cálculo.
5. **Campanha de ruído (Sec. 4.7, Tab. 7, Fig. 5).** Com σ = 0,1 K, TV ≈ 725–775 L/min, ou seja, perto do teto de 800: a válvula opera em *chattering* à taxa máxima, sem filtro de medição. As diferenças de TV desaparecem e a "frente" TV × IAE livre de ruído (Fig. 4) deixa de ser proxy de desgaste. Com n = 30, as diferenças entre Optimal ITAE (4,16 ± 0,63), AMIGO (4,38 ± 0,92) e TL (4,58 ± 0,81) estão dentro de um desvio-padrão; sem testes pareados apesar de sementes fixas. Das "1200 simulações", 240 são réplicas determinísticas (σ = 0); restam 960 estocásticas.
6. **Otimização avaliada no mesmo cenário em que foi ajustada (Sec. 3.4 item 7, Tab. 2).** O ITAE ótimo é minimizado no degrau de −2 K em que é avaliado; as demais regras não. "Mais rápido laço robusto" é parcialmente tautológico. Faltam degraus fora da amostra (±1, +2, ±5 K). Na regulação (Tab. 5) o ITAE ótimo perde para ZN, CC e AMIGO. A restrição é por penalidade (Ms = 1,60 reportado), com Nelder–Mead de 3 inícios. O 2-DOF ótimo apenas acrescenta β = 0,5 aos ganhos 1-DOF (IAE +31%, ITAE +108%); deveria ser reotimizado com β livre. A frente escalarizada (Fig. 4a) não define IAE₀/TV₀ nem diz se Ms ≤ 1,6 é aplicado.
7. **Perturbação de carga encostada no limite físico (Sec. 4.5, Tab. 5).** Com Tf + 5 K e CAf + 20%, calculei a vazão estacionária necessária em 396,65 K: **297,3 L/min**, a 2,7 L/min do fundo de escala. Todos os laços têm desvio de pico quase igual (7,22–7,41 K) e saturam. O ranking reflete a dinâmica de saturação, não a sintonia. A igualdade 1-DOF/2-DOF é tautológica (setpoint constante em y\_ss, β não atua). Usar amplitudes graduadas com margem de saturação explícita.
8. **Sobol (Sec. 4.8, Tab. 8).** Não se informa se cada rodada parte do equilíbrio nominal ou do equilíbrio da planta perturbada; no primeiro caso o IAE mede rejeição de um degrau paramétrico e a conclusão "governada pela física" é quase trivial. A leitura "margem de remoção de calor" não é testada (correlacionar IAE com Q\_r,max − Q\_g). Sem intervalos de confiança (N = 512; ΣS\_T chega a 1,39); sem tratamento de rodadas divergentes; faixas assimétricas e não justificadas (UA ∈ \[0,65; 1,05\]). O resumo diz que a TV de "laços de baixa margem" é movida por cinética e atraso, mas só ZN tem θ dominante; TL e 2-DOF ótimo são dominados por E\_a/R, AMIGO por C\_Af (S\_T = 0,623) e 2-DOF ótimo tem Ms = 1,6.
9. **Ponto de operação benigno (Sec. 2).** Planta estável em malha aberta, dominada por atraso (θ/τ = 0,146) e sem multiplicidade (o manuscrito 3 confirma raiz única); a Introdução motiva o problema com instabilidade e multiplicidade que aqui não existem. ZN/CC "funcionam" porque o atraso do FOPTD é aparente. Um teste com atraso de sensor real no degrau nominal (Ms e margem de atraso vs θ\_sensor) mostraria o risco verdadeiro. O título/resumo generalizam para "exothermic reactors".
10. **Literatura (Refs.).** Cerca de 29 referências, quase todas de 1942–2010; faltam trabalhos de 2019–2026 sobre anti-windup com limite de taxa, benchmarks de PID em CSTR e PID ótimo com restrição de Ms.

**Problemas menores**

- Mp e t\_s sem definição (critério de faixa); ITAE sem unidade (K·min²) na Tab. 2; Tab. 6 repete a Tab. 2 com arredondamento diferente (Ti = 0,19 vs 0,187).
- SIMC com τc = 0,40 min (≈ 4,3θ) e Td = 0,33θ: justificar; o ranking depende dessa escolha (comparar a Ms igual).
- Eq. (15): pesos aplicados ao desvio de y\_ss fixo, não ao setpoint corrente; esclarecer para sequências de setpoint. TL é regra para PI usada em forma PID.
- Fig. 2 e Fig. 5 com legendas densas; Fig. 4(b) com dois eixos de erro difíceis de ler.
- Sem CRediT, ORCID vazio, sem declaração de IA generativa; repositório sem DOI/versão arquivada.

| Critério | Peso | Nota R1 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 45 |
| Aderência ao escopo e relevância | 10% | 40 |
| Revisão da literatura e posicionamento | 10% | 50 |
| Metodologia e rigor | 20% | 55 |
| Resultados e análise | 15% | 60 |
| Discussão e conclusões | 10% | 50 |
| Redação, estrutura e apresentação | 10% | 75 |
| Conformidade com normas e referências | 5% | 70 |
| **Nota global (ponderada)** |  | **54/100** |

## Revisor 2 — Dr(a). em engenharia de processos e controle aplicado · perfil amigável e construtivo

**Avaliação geral.** Um trabalho cuidadoso, honesto sobre as próprias limitações e com uma pergunta prática que engenheiros de planta se fazem: por que sintonias clássicas "falham" em reatores exotérmicos? A resposta proposta (a implementação do anti-windup, e não a regra de sintonia) é útil e merece ser publicada, desde que o texto seja recalibrado: a ablação precisa ser completada e o enquadramento deve ser o de um estudo de benchmark com atuador realista, não o de uma nova técnica de sintonia.

**Pontos fortes**

1. **Atuador realista como eixo do estudo.** Limites de amplitude (0–300 L/min) e de taxa (80 L/min², 1,6 L/min por amostra) são tratados como parte da planta, não como detalhe de simulação. Poucos benchmarks de CSTR fazem isso, e é o que torna as conclusões transferíveis para a prática.
2. **Reprodutibilidade acima da média.** Parâmetros em tabela, passo de amostragem, sementes fixas e repositório citado. Pude refazer o equilíbrio e os valores de Ms/PM da planta linearizada, e eles conferem com o texto.
3. **Comparação ampla e organizada.** Sete regras de sintonia (ZN, CC, TL, AMIGO, 2-DOF, SIMC, ITAE ótimo com restrição de Ms) sob o mesmo protocolo, com a frente TV × IAE (Fig. 4) deixando claro o compromisso entre velocidade e desgaste da válvula.
4. **Mensagem central clara e pedagógica.** A ideia de que o mesmo ZN/CC "falha" ou "funciona" conforme o anti-windup é didática e relevante para ensino e para a indústria; a Eq. (13) é simples de implementar.
5. **Análise de sensibilidade global.** Usar Sobol/Saltelli para ranquear fatores de incerteza (Sec. 4.8) vai além do usual em estudos de sintonia e abre caminho para a discussão de robustez física.
6. **Redação e figuras.** Texto em inglês limpo, estrutura IMRaD, tabelas legíveis. A honestidade sobre o caso em que o ITAE ótimo perde na regulação (Tab. 5) é um ponto positivo.

**Sugestões construtivas**

- **Completar a ablação (2×2).** Incluir "sem anti-windup", *back-calculation* e as quatro combinações amplitude × taxa × sinal. Com isso a afirmação central passa de plausível a demonstrada, e o "842,5%" idêntico de ZN e CC deixa de ser um número sem mecanismo.
- **Reposicionar a contribuição.** Dado o escopo do JPC, apresentar o artigo como estudo de implementação (atuador com limite de taxa, anti-windup direcional, avaliação sob ruído) e, no resumo, evitar a linguagem de "melhor sintonia". Se houver dúvida, vale consultar o editor com uma carta de pré-submissão.
- **Reescrever a explicação de robustez com a planta exata.** Mostrar Ms e ‖CS‖∞ na linearização, não no FOPTD, e relacionar o ruído ao ganho de alta frequência. Isso fortalece a conclusão 2 em vez de enfraquecê-la.
- **Dar uma chance justa ao ITAE ótimo.** Avaliar em degraus fora da amostra (±1, +2, ±5 K) e reotimizar o 2-DOF com β livre; o resultado provavelmente continua interessante e passa a ser defensável.
- **Ruído com filtro de medição.** Incluir uma coluna com derivada filtrada (N menor) ou filtro de primeira ordem no sensor; isso aproxima o estudo da prática industrial e devolve significado ao TV.
- **Perturbação de carga com margem.** Trocar Tf + 5 K / CAf + 20% por amplitudes graduadas, de modo que o resfriamento não sature (a vazão estacionária exigida é ≈ 297 L/min), e mostrar a margem de saturação.
- **Explicitar o ponto de operação.** Dizer na Introdução que o caso é estável em malha aberta e dominado por atraso, e que a multiplicidade e a instabilidade ficam para trabalhos futuros (o manuscrito companheiro sobre controlabilidade pode ser citado como ponte).
- **Atualizar a literatura** (2019–2026) sobre anti-windup com limite de taxa e sobre benchmarks de PID em CSTR; hoje as referências são majoritariamente anteriores a 2010.
- **Detalhes de apresentação.** Definir Mp e t\_s, colocar unidades no ITAE, fundir as Tab. 2 e 6, simplificar as legendas das Fig. 2 e 5, e acrescentar CRediT, ORCID e declaração de uso de IA generativa.

| Critério | Peso | Nota R2 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 58 |
| Aderência ao escopo e relevância | 10% | 55 |
| Revisão da literatura e posicionamento | 10% | 60 |
| Metodologia e rigor | 20% | 68 |
| Resultados e análise | 15% | 70 |
| Discussão e conclusões | 10% | 62 |
| Redação, estrutura e apresentação | 10% | 82 |
| Conformidade com normas e referências | 5% | 75 |
| **Nota global (ponderada)** |  | **65/100** |

## Revisor 3 — Dr(a). em sistemas dinâmicos e metodologia científica · perfil imparcial

**Avaliação geral.** O manuscrito tem um núcleo útil (atuador realista + anti-windup direcional) cercado por análises de valor desigual. Os dois revisores anteriores estão essencialmente certos, em momentos diferentes: R1 acerta ao apontar que a ablação central é fraca e que parte das conclusões tem atribuição causal indevida; R2 acerta ao notar que o desenho do estudo é reaproveitável e honesto. O que decide o destino em um A1 é o escopo do periodíco e a profundidade da evidência da tese principal.

**Pontos fortes**

- Atuador com limite de amplitude e de taxa tratado como parte da planta; protocolo único para sete regras de sintonia.
- Números verificáveis: o equilíbrio, Ms/PM da planta linearizada e as ordens de grandeza de TV conferem com recomputação independente.
- Uso de Sobol/Saltelli e de frente TV × IAE, acima do padrão de estudos de sintonia.
- Transparência razoável: o artigo mostra os casos em que a proposta não ganha (regulação, Tab. 5).
- Redação e estrutura de bom nível.

**Pontos fracos**

- **Tese central sustentada por comparação assimétrica.** A regra "ingênua" equivale a não ter anti-windup para Kp < 0; sem a condição "sem AW" e sem *back-calculation*, a conclusão "a implementação decide" é plausível, mas não demonstrada, e o "842,5%" tem explicação trivial (válvula presa em 100%).
- **Escopo.** O JPC exclui PID tuning; o risco de *desk reject* é real e independente da qualidade técnica.
- **Explicações de mecanismo contraditórias** (Ms do FOPTD usado na Sec. 4.7 depois de reconhecido como artefato na Sec. 4.4).
- **Cenários que não discriminam:** a carga exige ≈ 297 L/min (a 2,7 do fundo de escala); o ruído de 0,1 K leva TV a ≈ 725–775 de um teto de ≈ 800; o ITAE ótimo é avaliado no cenário em que foi ajustado.
- **Sobol sem especificação completa** (ponto de partida, IC, divergências) e interpretação física não testada.
- **Originalidade modesta** quanto à Eq. (13) e literatura recente ausente.

**Plano de melhoria**

*Indispensável*

1. Completar a ablação: sem AW, *back-calculation*, clamping sensível/insensível ao sinal × amplitude × taxa (2×2), com mecanismo identificado.
2. Reposicionar o artigo no escopo do JPC (estudo de implementação/benchmark com atuador realista) ou submeter a periódico de sintonia/educação em controle; reescrever título, resumo e destaques.
3. Reavaliar robustez pela planta exata (Ms, ‖CS‖∞, ganho de alta frequência) e corrigir a Sec. 4.4/4.7 e a Conclusão 2.
4. Refazer a campanha de ruído com filtro de medição e testes pareados; refazer a perturbação de carga com margem de saturação.
5. Avaliação fora da amostra do ITAE ótimo e reotimização do 2-DOF com β livre.

*Fortalece*

6. Delimitar a novidade da Eq. (13) frente a *conditional integration* e esquemas com limite de taxa; atualizar a literatura (2019–2026).
7. Completar o Sobol: ponto de partida, IC, tratamento de divergências, teste da margem de remoção de calor.
8. Adicionar atraso de sensor real e margem de atraso no ponto nominal.
9. Esclarecer definições (Mp, t\_s, ITAE com unidades), pesos da Eq. (15) e a escolha de τc do SIMC.

*Desejável*

10. Ponto de operação mais exigente (próximo à multiplicidade) como segundo caso.
11. Fundir Tab. 2 e 6, simplificar Fig. 2/5, CRediT, ORCID, declaração de IA generativa e repositório com DOI.

| Critério | Peso | Nota R3 |
| --- | --- | --- |
| Originalidade e contribuição | 20% | 52 |
| Aderência ao escopo e relevância | 10% | 45 |
| Revisão da literatura e posicionamento | 10% | 54 |
| Metodologia e rigor | 20% | 62 |
| Resultados e análise | 15% | 64 |
| Discussão e conclusões | 10% | 56 |
| Redação, estrutura e apresentação | 10% | 78 |
| Conformidade com normas e referências | 5% | 72 |
| **Nota global (ponderada)** |  | **59/100** |

## Discussão entre os revisores

**Ponto 1 — Escopo (JPC).** *R1:* o JPC exclui PID tuning; mesmo tecnicamente impecável, o manuscrito corre risco de *desk reject*. *R2:* o recorte de "atuador realista + anti-windup direcional" pode ser lido como estudo de implementação. *R3:* o texto atual (título, resumo e destaques) vende sintonia, não implementação; a leitura de R2 só vale se o artigo for reescrito. **Resolução:** R2 concorda que, como está, o escopo é fraco; nota de escopo rebaixada para 42 e reposicionamento vira exigência obrigatória.

**Ponto 2 — Ablação do anti-windup.** *R1:* sem a condição "sem AW", *back-calculation* e o 2×2, a tese central não está demonstrada; o 842,5% é válvula presa em 100%. *R2:* a tese é plausível e didática. *R3:* plausível ≠ demonstrado; e a regra "ingênua" nunca dispara para Kp < 0. **Resolução:** R2 aceita; a ablação completa é exigência obrigatória e a Introdução não pode afirmar que "a literatura atribui a falha à regra" sem citação específica.

**Ponto 3 — Robustez e ruído.** *R1:* Ms do FOPTD é artefato; o ruído é governado pelo ganho de alta frequência (|Kp|(1+N) = 490/559/77). *R3:* confirma a recomputação e acrescenta que TV ≈ 725–775 de um teto de ≈ 800 elimina o poder de discriminação da campanha. *R2:* concorda, mas lembra que a conclusão "robustez, não estabilidade" pode ser salva se reescrita com ‖CS‖∞ na planta exata. **Resolução:** consenso em reescrever a Sec. 4.4/4.7 e refazer o ruído com filtro.

**Ponto 4 — ITAE ótimo e carga.** *R1:* otimizado e avaliado no mesmo cenário; carga a 2,7 L/min do fundo de escala. *R2:* sugere amplitudes graduadas e degraus fora da amostra. *R3:* acrescenta a reotimização do 2-DOF com β livre. **Resolução:** unanimidade.

**Ponto 5 — Nota e decisão.** R1 (54) e R2 (65) divergiam em 11 pontos; a diferença vem do peso dado ao escopo e à ablação. R3 (59) propõe a média ponderada pelos pontos acordados. **Resolução:** os experimentos exigidos (ablação completa, novo ruído, nova carga, avaliação fora da amostra) são uma campanha nova, não um ajuste; por isso a banda de rejeição com incentivo à resubmissão, e não a de revisão maior. R2 aceita, registrando que os números são corretos e que o desenho do estudo merece ser aproveitado.

## Consenso, decisão e exigências

| Critério | Peso | R1 | R2 | R3 | Consenso |
| --- | --- | --- | --- | --- | --- |
| Originalidade e contribuição | 20% | 45 | 58 | 52 | 52 |
| Aderência ao escopo e relevância | 10% | 40 | 55 | 45 | 42 |
| Revisão da literatura e posicionamento | 10% | 50 | 60 | 54 | 54 |
| Metodologia e rigor | 20% | 55 | 68 | 62 | 60 |
| Resultados e análise | 15% | 60 | 70 | 64 | 64 |
| Discussão e conclusões | 10% | 50 | 62 | 56 | 54 |
| Redação, estrutura e apresentação | 10% | 75 | 82 | 78 | 78 |
| Conformidade com normas e referências | 5% | 70 | 75 | 72 | 72 |
| **Nota global (ponderada)** |  | **54** | **65** | **59** | **58/100** |

**Decisão (Qualis A1, Journal of Process Control): rejeição com incentivo à resubmissão (banda 45–61).** A nota de 58 reflete um trabalho numericamente íntegro e bem escrito, cujo principal obstáculo é o escopo do período e a evidência insuficiente da tese central.

**Exigências obrigatórias**

1. Ablação completa do anti-windup: sem AW, *back-calculation* e 2×2 (amplitude × taxa × sinal), com o mecanismo identificado.
2. Reposicionar o artigo no escopo do JPC (estudo de implementação/benchmark com atuador realista) e reescrever título, resumo e destaques; ou escolher outro período.
3. Robustez pela planta exata (Ms, ‖CS‖∞, ganho de alta frequência); corrigir as Sec. 4.4/4.7 e a Conclusão 2.
4. Refazer a campanha de ruído com filtro de medição e testes pareados; refazer a carga com margem de saturação.
5. Avaliação do ITAE ótimo fora da amostra e reotimização do 2-DOF com β livre.

**Exigências recomendadas**

6. Delimitar a novidade da Eq. (13) e atualizar a literatura (2019–2026).
7. Completar o Sobol (ponto de partida, IC, divergências, teste da margem de remoção de calor).
8. Atraso de sensor real e margem de atraso; declarar a limitação do ponto de operação estável e dominado por atraso.
9. Definir Mp, t\_s e unidades; justificar τc do SIMC; fundir Tab. 2 e 6.
10. CRediT, ORCID, declaração de uso de IA generativa e repositório com DOI.

**Conclusão da revisão por pares**

O manuscrito apresenta um estudo comparativo de sete sintonias de PID em um CSTR exotérmico com válvula limitada em amplitude e taxa, e argumenta que a falha atribuída a ZN e CC decorre da implementação do anti-windup, e não da regra de sintonia. O trabalho é bem escrito, reprodutível e numericamente consistente (os valores de equilíbrio e de Ms/PM puderam ser reproduzidos). Contudo, a tese central repousa em uma ablação incompleta, na qual a regra "ingênua" equivale a não ter anti-windup; a explicação de robustez usa uma métrica do modelo FOPTD que os próprios autores reconhecem como artefato; e os cenários de ruído e de carga operam perto dos limites físicos do atuador, o que reduz o poder de discriminação entre sintonias. Soma-se a isso o fato de o escopo do Journal of Process Control excluir a sintonia de PID e suas variantes. Recomenda-se a rejeição nesta forma, com incentivo a uma resubmissão que complete a ablação, refaça as campanhas de ruído e de carga e reposicione a contribuição como estudo de implementação. O núcleo experimental merece ser aproveitado.
