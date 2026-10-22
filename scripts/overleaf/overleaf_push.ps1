# overleaf_push.ps1
# ============================================================
# Envia arquivos LaTeX locais → Overleaf.
#
# Uso: .\overleaf_push.ps1 -ProjectName "Nome do Projeto no Overleaf"
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName
)

$base    = $PSScriptRoot
$ols     = "$base\.tools-venv\Scripts\ols.exe"
$artigos = "$base\Artigos_Rascunhos\Artigo_01_Classic_Methods\overleaf"

Write-Host "=== LOCAL → OVERLEAF ===" -ForegroundColor Cyan
Write-Host "`nEnviando arquivos locais para '$ProjectName' no Overleaf..." -ForegroundColor Yellow

# O flag --local-only esta no comando raiz 'ols', nao em subcomandos
& $ols --local-only --name $ProjectName --path $artigos

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nConcluido! Verifique: https://www.overleaf.com/project" -ForegroundColor Green
} else {
    Write-Host "`nErro no envio. Tente: ols list (para ver nomes dos projetos)" -ForegroundColor Red
}
