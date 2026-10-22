# overleaf_pull.ps1
# ============================================================
# Baixa o projeto do Overleaf → pasta local → push para GitHub.
#
# Uso: .\overleaf_pull.ps1 -ProjectName "Nome do Projeto no Overleaf"
#
# O ProjectName deve ser o nome EXATO listado pelo overleaf_setup.ps1
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    [string]$Token = $env:GITHUB_TOKEN
)

$base    = $PSScriptRoot
$python  = "$base\.tools-venv\Scripts\python.exe"
$syncPy  = "$base\overleaf_sync.py"
$artigos = "$base\Artigos_Rascunhos\Artigo_01_Classic_Methods\overleaf"

Write-Host "=== OVERLEAF → LOCAL → GITHUB ===" -ForegroundColor Cyan

# 1. Baixar codigo-fonte completo (.tex, .bib, figuras) do Overleaf
Write-Host "`n[1/3] Baixando '$ProjectName' do Overleaf..." -ForegroundColor Yellow
& $python $syncPy --pull $ProjectName --dest "Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro ao baixar do Overleaf. Liste seus projetos com: python overleaf_sync.py --list" -ForegroundColor Red
    exit 1
}

# 2. Detectar arquivos alterados
$changed = Get-ChildItem -Path $artigos -Recurse -File |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } |
    Select-Object Name, LastWriteTime

Write-Host "`n[2/3] Arquivos atualizados:" -ForegroundColor Yellow
if ($changed.Count -eq 0) {
    Write-Host "  Nenhuma alteracao detectada." -ForegroundColor DarkGray
    exit 0
}
$changed | ForEach-Object { Write-Host "  + $($_.Name)" -ForegroundColor Green }

# 3. Push para GitHub
Write-Host "`n[3/3] Sincronizando com GitHub..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
& "$base\sync_to_github.ps1" -Message "paper: pull from Overleaf [$timestamp]" -Token $Token

Write-Host "`nConcluido! Overleaf → Local → GitHub." -ForegroundColor Green
