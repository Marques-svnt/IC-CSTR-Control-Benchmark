# sync_to_github.ps1
# ============================================================
# Script de sincronização do projeto IC com GitHub
# Uso: .\sync_to_github.ps1 -Message "descrição do que foi feito"
#
# Requer: token do GitHub com permissão 'repo'
# Após instalar Git com admin, este script pode ser aposentado.
# ============================================================

param(
    [string]$Message = "chore: sync project files",
    [string]$Token   = $env:GITHUB_TOKEN,
    [string]$Branch  = "feature/artigo-01-pid-classical"
)

if (-not $Token) {
    $Token = [Environment]::GetEnvironmentVariable("GITHUB_TOKEN", "User")
}

$owner   = "Marques-svnt"
$repo    = "IC-PID-Neural-Agents"
$base    = (Get-Item $PSScriptRoot).Parent.Parent.FullName  # raiz do IC (scripts/github/../../)
$apiBase = "https://api.github.com/repos/$owner/$repo/contents"

if (-not $Token) {
    Write-Host "ERRO: Token nao definido. Use -Token ou defina a variavel de ambiente GITHUB_TOKEN." -ForegroundColor Red
    exit 1
}

$headers = @{
    "Authorization"        = "Bearer $Token"
    "Accept"               = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

function Get-RemoteFile {
    param([string]$RepoPath)
    try {
        $r = Invoke-RestMethod -Uri "$apiBase/$RepoPath`?ref=$Branch" -Headers $headers -ErrorAction Stop
        return $r
    } catch { return $null }
}

function Push-File {
    param([string]$LocalPath, [string]$RepoPath)
    $localItem = Get-Item $LocalPath
    $remote = Get-RemoteFile -RepoPath $RepoPath

    # Se o arquivo já existe no GitHub e tem o mesmo tamanho em bytes, pula o envio
    if ($remote -and ($remote.size -eq $localItem.Length)) {
        Write-Host "  [UP-TO-DATE] $RepoPath" -ForegroundColor DarkGray
        return
    }

    $bytes  = [IO.File]::ReadAllBytes($LocalPath)
    $b64    = [Convert]::ToBase64String($bytes)
    $sha    = if ($remote) { $remote.sha } else { $null }

    $bodyObj = @{ message = $Message; content = $b64; branch = $Branch }
    if ($sha) { $bodyObj.sha = $sha }   # necessário para UPDATE de arquivo existente

    $body = $bodyObj | ConvertTo-Json -Compress
    try {
        $r = Invoke-RestMethod -Uri "$apiBase/$RepoPath" -Method PUT `
             -Headers $headers -Body $body -ContentType "application/json; charset=utf-8" -ErrorAction Stop
        Write-Host "  OK  $RepoPath" -ForegroundColor Green
    } catch {
        Write-Host "  ERR $RepoPath : $_" -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 250
}

# ============================================================
# Arquivos a sincronizar (adicionar novos aqui conforme necessário)
# Formato: @("caminho\local\relativo", "caminho/remoto/no/repo")
# ============================================================
$files = @(
    # Raiz
    @("README.md",                      "README.md"),
    @(".gitignore",                     ".gitignore"),
    @("pyproject.toml",                 "pyproject.toml"),
    @("requirements.txt",               "requirements.txt"),

    # Projeto - fases
    @("Projeto\README.md",                                                 "Projeto/README.md"),
    @("Projeto\Fase_1_Revisao_Bibliografica\README.md",                    "Projeto/Fase_1_Revisao_Bibliografica/README.md"),
    @("Projeto\Fase_2_Modelagem_Matematica\README.md",                     "Projeto/Fase_2_Modelagem_Matematica/README.md"),
    @("Projeto\Fase_3_PID_Classico\README.md",                             "Projeto/Fase_3_PID_Classico/README.md"),
    @("Projeto\Fase_4_Redes_Neurais\README.md",                            "Projeto/Fase_4_Redes_Neurais/README.md"),
    @("Projeto\Fase_5_Multi_Agente_LangGraph\README.md",                   "Projeto/Fase_5_Multi_Agente_LangGraph/README.md"),
    @("Projeto\Fase_6_Comparacao_Resultados\README.md",                    "Projeto/Fase_6_Comparacao_Resultados/README.md"),

    # Artigo 01
    @("Artigos_Rascunhos\README.md",                                                         "Artigos_Rascunhos/README.md"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\main.tex",                         "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/main.tex"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\references.bib",                   "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/references.bib"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\sections\01_introduction.tex",     "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/sections/01_introduction.tex"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\sections\02_modeling.tex",         "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/sections/02_modeling.tex"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\sections\03_pid_classical.tex",    "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/sections/03_pid_classical.tex"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\sections\04_neural_pid.tex",       "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/sections/04_neural_pid.tex"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\sections\05_multiagent.tex",       "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/sections/05_multiagent.tex"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\sections\06_results.tex",          "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/sections/06_results.tex"),
    @("Artigos_Rascunhos\Artigo_01_PID_Neural_Comparativo\sections\07_conclusion.tex",       "Artigos_Rascunhos/Artigo_01_PID_Neural_Comparativo/sections/07_conclusion.tex"),

    # Biblioteca
    @("Biblioteca\README.md",                                              "Biblioteca/README.md")
)

# ============================================================
# Detectar automaticamente arquivos em src/, tests/, experiments/, Projeto/, Artigos_Rascunhos, Biblioteca e exercises/
# ============================================================
Get-ChildItem -Path "$base\src" -Recurse -Include "*.py","*.md" | 
    Where-Object { 
        $_.FullName -notlike "*\__pycache__*" -and 
        $_.FullName -notlike "*\.egg-info*" 
    } | ForEach-Object {
        $rel = $_.FullName.Replace("$base\", "").Replace("\", "/")
        $loc = $_.FullName.Replace("$base\", "")
        if ($files -notcontains @($loc, $rel)) {
            $files += ,@($loc, $rel)
        }
    }

Get-ChildItem -Path "$base\tests" -Recurse -Include "*.py","*.md" | 
    Where-Object { 
        $_.FullName -notlike "*\__pycache__*" -and 
        $_.FullName -notlike "*\.pytest_cache*" 
    } | ForEach-Object {
        $rel = $_.FullName.Replace("$base\", "").Replace("\", "/")
        $loc = $_.FullName.Replace("$base\", "")
        if ($files -notcontains @($loc, $rel)) {
            $files += ,@($loc, $rel)
        }
    }

if (Test-Path "$base\experiments") {
    Get-ChildItem -Path "$base\experiments" -Recurse -Include "*.py","*.md" | 
        Where-Object { $_.FullName -notlike "*\__pycache__*" } | ForEach-Object {
            $rel = $_.FullName.Replace("$base\", "").Replace("\", "/")
            $loc = $_.FullName.Replace("$base\", "")
            if ($files -notcontains @($loc, $rel)) {
                $files += ,@($loc, $rel)
            }
        }
}

Get-ChildItem -Path "$base\Projeto" -Recurse -Include "*.py","*.ipynb","*.md" | ForEach-Object {
    $rel = $_.FullName.Replace("$base\", "").Replace("\", "/")
    $loc = $_.FullName.Replace("$base\", "")
    if ($files -notcontains @($loc, $rel)) {
        $files += ,@($loc, $rel)
    }
}

Get-ChildItem -Path "$base\Artigos_Rascunhos" -Recurse -Include "*.tex","*.bib","*.png","*.jpg","*.pdf","*.md" | ForEach-Object {
    $rel = $_.FullName.Replace("$base\", "").Replace("\", "/")
    $loc = $_.FullName.Replace("$base\", "")
    if ($files -notcontains @($loc, $rel)) {
        $files += ,@($loc, $rel)
    }
}

Get-ChildItem -Path "$base\Biblioteca" -Recurse -Include "*.pdf" | ForEach-Object {
    $rel = $_.FullName.Replace("$base\", "").Replace("\", "/")
    $loc = $_.FullName.Replace("$base\", "")
    if ($files -notcontains @($loc, $rel)) {
        $files += ,@($loc, $rel)
    }
}



# Sync scripts/ folder (github + overleaf helpers)
if (Test-Path "$base\scripts") {
    Get-ChildItem -Path "$base\scripts" -Recurse -Include "*.ps1","*.py" | ForEach-Object {
        $rel = $_.FullName.Replace("$base\", "").Replace("\", "/")
        $loc = $_.FullName.Replace("$base\", "")
        if ($files -notcontains @($loc, $rel)) {
            $files += ,@($loc, $rel)
        }
    }
}


# ============================================================
# Executar upload
# ============================================================
Write-Host "`n[sync_to_github] Iniciando sync: $Message" -ForegroundColor Cyan
Write-Host "Repo: https://github.com/$owner/$repo (Branch: $Branch)`n"

$ok = 0; $err = 0
foreach ($f in $files) {
    $full = Join-Path $base $f[0]
    if (Test-Path $full) {
        Push-File -LocalPath $full -RepoPath $f[1]
        $ok++
    } else {
        Write-Host "  SKIP (nao existe): $($f[0])" -ForegroundColor DarkGray
    }
}

Write-Host "`n[sync_to_github] Concluido: $ok arquivos sincronizados." -ForegroundColor Cyan
Write-Host "Ver em: https://github.com/$owner/$repo"
