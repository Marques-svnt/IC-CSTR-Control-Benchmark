# Pendências para o autor — Artigo 1 (JPC), v6

Itens que não posso decidir, verificar ou executar sem você. Atualizado a cada fase.

## Fase 1

1. **Títulos e periódicos dos artigos companheiros** (carta, parágrafo "Relation to the companion manuscripts"). O rascunho usa os títulos que estão nos `.bib` dos Artigos 2 e 3; confirme os títulos e periódicos vigentes.
2. **Carta: enquadramento "control applications".** Confirme se quer submeter sob esse rótulo; é a leitura dos revisores, não do editor.
3. **ORCID do segundo autor** (Elilton Rodrigues Edwards): não está no repositório; não vou inventar.
4. **Constantes do modelo no texto principal** (parâmetros da Tabela 2, estado estacionário 396,65 K, autovalores, G_true, FOPTD): são da v5 e vêm do código, mas não são macros geradas dos CSV; se quiser a regra 2 também para elas, preciso gerar um CSV de constantes do modelo.
5. **Avisos "citation multiply defined" no suplementar:** vêm do pacote `xr`, que importa as citações do `main.aux`; a numeração do suplementar é a dele mesmo (conferida). Decida se o suplementar deve ter bibliografia própria (como está) ou remeter à do artigo.

## Fase 3

6. **Licença do código:** não há arquivo `LICENSE` no repositório; o Zenodo exige uma licença. Escolha (por exemplo MIT, BSD-3-Clause ou GPL-3.0); não escolhi por você.
7. **Depósito no Zenodo** (aguarda sua aprovação): criar a tag de versão (proposta `v2.0.0-jpc`), publicar o release no GitHub com a integração Zenodo ativa ou fazer o upload manual, e substituir o placeholder `10.5281/zenodo.XXXXXXX` em `references.bib` (`andrade2026software`), `CITATION.cff` e `.zenodo.json`, e a data em `CITATION.cff`.
8. **Tag existente `v1.0.0-jpc-submission`** aponta para uma versão anterior; decida se ela fica, já que o README ainda tem o selo dela.
9. **Livros sem DOI** (Seborg, Åström e Hägglund 2006 e 1995, O'Dwyer, Shinskey, Luyben, Visioli, Bequette, Skogestad e Postlethwaite) e artigos antigos sem DOI (Ziegler–Nichols, Cohen–Coon, Åström–Rundqwist 1989): metadados mantidos da v5, não verificados no Crossref.

## Fases 2 e 4

10. **Hipóteses do parecer não verificadas com o nosso código** (ficaram fora do texto principal): perturbações físicas nos seis cantos factíveis (o revisor obteve M_s,lin máx. 1,30 para o ótimo exato) e intervalos dos efeitos de Shapley. Se quiser que o suplementar as traga, é uma rodada de código à parte.
11. **Diff em PDF:** o `latexdiff` não está instalado; entreguei o diff por palavras em `diff_v5_v6.txt`. Instale o `latexdiff` se quiser o PDF marcado.
12. **Extensão:** 12 páginas de artigo + a página de highlights que o template gera (13 no PDF). A carta trata isso como dentro do nominal; se preferir, peço uma justificativa curta.
