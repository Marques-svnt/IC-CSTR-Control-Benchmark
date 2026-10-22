# overleaf_setup.ps1
# ============================================================
# Configuração INICIAL — rode UMA VEZ para autenticar.
# Salva um cookie de sessão local (nenhuma senha é armazenada
# em texto plano).
#
# Uso: .\overleaf_setup.ps1
# ============================================================

$base = $PSScriptRoot
$ols  = "$base\.tools-venv\Scripts\ols.exe"

Write-Host "=== CONFIGURACAO INICIAL OVERLEAF-SYNC ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Digite suas credenciais do Overleaf (email e senha)."
Write-Host "Elas sao usadas apenas para gerar um cookie de sessao local." -ForegroundColor DarkGray
Write-Host ""

# Login interativo — solicita email e senha no terminal
& $ols login

Write-Host ""
Write-Host "Listando seus projetos Overleaf..." -ForegroundColor Yellow
& $ols list

Write-Host ""
Write-Host "Copie o NOME EXATO do seu projeto acima e use-o no overleaf_pull.ps1" -ForegroundColor Green
Write-Host "(parametro -ProjectName)"
