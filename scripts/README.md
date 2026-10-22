# Scripts de Manutenção e Sincronização (`scripts/`)

> Utilitários auxiliares de manutenção do projeto e sincronização. Não fazem parte do código-fonte científico de simulação da planta.

---

## 1. Controle de Versão e Git

O fluxo primário de controle de versão é operado via **Git nativo** e chaves SSH:

```bash
# Enviar alterações para o repositório oficial
git add .
git commit -m "feat/fix: mensagem semântica"
git push origin main
```

O script PowerShell legado `scripts/github/sync_to_github.ps1` permanece disponível para ambientes Windows legados que utilizem a REST API do GitHub.

---

## 2. Integração com Overleaf (`scripts/overleaf/`)

| Script | Finalidade |
|---|---|
| `overleaf_push.ps1` | Upload automatizado de fontes LaTeX para o Overleaf. |
| `overleaf_pull.ps1` | Download local de alterações efetuadas diretamente no Overleaf. |
| `overleaf_setup.ps1` | Configuração inicial de autenticação do Overleaf. |
| `overleaf_sync.py` | Módulo Python de sincronização acionado pelos scripts PowerShell. |

> [!CAUTION]
> **Segurança de Credenciais:** O arquivo de sessão `.olauth` é **estritamente ignorado pelo Git** (`.gitignore`) para prevenir qualquer exposição acidental de tokens de autenticação ou cookies de sessão.
