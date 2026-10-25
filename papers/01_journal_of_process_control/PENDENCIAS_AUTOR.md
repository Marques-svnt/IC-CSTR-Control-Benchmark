# Pendências para o autor — Artigo 1 (JPC), v6

Itens que não posso decidir, verificar ou executar sem você. Atualizado a cada fase.

## Fase 1

1. **Títulos e periódicos dos artigos companheiros** (carta, parágrafo "Relation to the companion manuscripts"). O rascunho usa os títulos que estão nos `.bib` dos Artigos 2 e 3; confirme os títulos e periódicos vigentes.
2. **Carta: enquadramento "control applications".** Confirme se quer submeter sob esse rótulo; é a leitura dos revisores, não do editor.
3. **ORCID do segundo autor** (Elilton Rodrigues Edwards): não está no repositório; não vou inventar.
4. **Constantes do modelo no texto principal** (parâmetros da Tabela 2, estado estacionário 396,65 K, autovalores, G_true, FOPTD): são da v5 e vêm do código, mas não são macros geradas dos CSV; se quiser a regra 2 também para elas, preciso gerar um CSV de constantes do modelo.
5. **Avisos "citation multiply defined" no suplementar:** vêm do pacote `xr`, que importa as citações do `main.aux`; a numeração do suplementar é a dele mesmo (conferida). Decida se o suplementar deve ter bibliografia própria (como está) ou remeter à do artigo.
