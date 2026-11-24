# auri-jarvis — környezet telepítése (owner: AI-3).
# Futtatás az auri-jarvis mappából:   powershell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1
#
# 1) Python 3.12 venv + a pinelt csomagok (requirements.txt)
# 2) .env létrehozása a .env.example-ből (ha még nincs)
# 3) Ollama-lépések (spec 10. fejezet): CSAK KIÍRJA, és rákérdez — magától nem futtat
#    rendszerszintű változtatást (winget, felhasználói környezeti változók, modellek letöltése)
# 4) python -m auri_jarvis --selftest
param(
    [switch]$NoOllama  # a 3. lépés kihagyása
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host "== auri-jarvis telepítés: $root" -ForegroundColor Cyan

# ── 1) venv + csomagok ──────────────────────────────────────────────────────
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "-- venv létrehozása (Python 3.12)…"
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Nem sikerült a venv (kell a Python 3.12: py -3.12)." }
}
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "A csomagok telepítése sikertelen." }
& $py -m pip check

# ── 2) .env ─────────────────────────────────────────────────────────────────
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "-- .env létrehozva a mintából. Töltsd ki (ElevenLabs, Supabase) — titok, gitre nem kerül." -ForegroundColor Yellow
} else {
    Write-Host "-- .env megvan (nem nyúlok hozzá)."
}

# ── 3) Ollama (rendszerszintű → csak jóváhagyással) ─────────────────────────
if (-not $NoOllama) {
    $models = @("qwen3.5:4b", "gemma4:e4b", "embeddinggemma")
    $modelsDir = Join-Path (Split-Path -Parent $root) "PublicFreeAI\Ollama"
    $haveOllama = [bool](Get-Command ollama -ErrorAction SilentlyContinue)
    $userModels = [Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
    Write-Host ""
    Write-Host "== Ollama (spec 10. fejezet) — ezek RENDSZERSZINTŰ lépések:" -ForegroundColor Cyan
    if (-not $haveOllama) { Write-Host "   winget install Ollama.Ollama" }
    if ($userModels -ne $modelsDir) {
        Write-Host "   [Environment]::SetEnvironmentVariable('OLLAMA_MODELS', '$modelsDir', 'User')   (most: '$userModels')"
    }
    Write-Host "   [Environment]::SetEnvironmentVariable('OLLAMA_NUM_PARALLEL', '1', 'User')"
    Write-Host "   [Environment]::SetEnvironmentVariable('OLLAMA_KV_CACHE_TYPE', 'q8_0', 'User')"
    foreach ($m in $models) { Write-Host "   ollama pull $m" }
    $ans = Read-Host "Futtassam most ezeket? (i = igen, bármi más = nem)"
    if ($ans -eq "i") {
        if (-not $haveOllama) { winget install Ollama.Ollama }
        if ($userModels -ne $modelsDir) { [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $modelsDir, "User") }
        [Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
        [Environment]::SetEnvironmentVariable("OLLAMA_KV_CACHE_TYPE", "q8_0", "User")
        Write-Host "-- Az Ollamát indítsd újra (tálca → Quit, majd újra), és nyiss új PowerShellt." -ForegroundColor Yellow
        if (Get-Command ollama -ErrorAction SilentlyContinue) {
            foreach ($m in $models) { ollama pull $m }
        }
    } else {
        Write-Host "-- Kihagyva. Később kézzel: lásd fent."
    }
}

# ── 4) önellenőrzés ─────────────────────────────────────────────────────────
Write-Host ""
& $py -m auri_jarvis --selftest
Write-Host ""
Write-Host "Kész. Indítás:  .\.venv\Scripts\python -m auri_jarvis        (hang + HUD)" -ForegroundColor Green
Write-Host "                .\.venv\Scripts\python -m auri_jarvis --text (szöveges próba)" -ForegroundColor Green
