# Auri J.A.R.V.I.S. automatikus indítása bejelentkezéskor (owner: AI-3, spec 5.10).
#
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1              # telepítés (rákérdez)
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1 -Uninstall   # eltávolítás
#   … -Yes                                                                                   # kérdés nélkül (ha már jóváhagytad)
#
# Feladatütemező-feladat a SAJÁT felhasználódnak (nem rendszergazdai): bejelentkezés után
# 30 s-mal (hogy az Ollama előbb elinduljon) elindítja a `.venv\Scripts\pythonw.exe -m auri_jarvis`
# parancsot konzolablak nélkül. Hiba esetén percenként legfeljebb 3× újraindítja; egyszerre csak
# egy példány fut (a daemon maga is ellenőrzi). Naplók: data\body\logs\jarvis.log
param(
    [switch]$Uninstall,
    [int]$DelaySeconds = 30,
    [switch]$Yes  # already approved by the user → don't ask (non-interactive runs)
)
$ErrorActionPreference = "Stop"
$TaskName = "Auri JARVIS"
$root = Split-Path -Parent $PSScriptRoot
$pyw = Join-Path $root ".venv\Scripts\pythonw.exe"
$user = "$env:USERDOMAIN\$env:USERNAME"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($Uninstall) {
    if (-not $existing) { Write-Host "Nincs ilyen feladat: $TaskName"; exit 0 }
    $ans = if ($Yes) { "i" } else { Read-Host "Töröljem a(z) '$TaskName' automatikus indítást? (i = igen)" }
    if ($ans -eq "i") {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Törölve." -ForegroundColor Green
    } else {
        Write-Host "Nem töröltem."
    }
    exit 0
}

if (-not (Test-Path $pyw)) { throw "Nincs .venv ($pyw) — előbb: .\scripts\setup_env.ps1" }

Write-Host "Ez egy Feladatütemező-feladatot hoz létre:" -ForegroundColor Cyan
Write-Host "  név:          $TaskName$(if ($existing) { '  (a meglévőt felülírja)' })"
Write-Host "  felhasználó:  $user (normál jogokkal, csak bejelentkezve)"
Write-Host "  mikor:        bejelentkezéskor, $DelaySeconds s késleltetéssel"
Write-Host "  parancs:      `"$pyw`" -m auri_jarvis"
Write-Host "  mappa:        $root"
Write-Host "  hiba esetén:  percenként újraindítás, legfeljebb 3×"
$ans = if ($Yes) { "i" } else { Read-Host "Létrehozzam? (i = igen)" }
if ($ans -ne "i") { Write-Host "Nem hoztam létre."; exit 0 }

$action = New-ScheduledTaskAction -Execute $pyw -Argument "-m auri_jarvis" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$trigger.Delay = "PT$($DelaySeconds)S"
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Description "Auri J.A.R.V.I.S. — helyi hangasszisztens (auri-jarvis)" -Force | Out-Null

Write-Host "Kész: a következő bejelentkezéskor indul. Most azonnal: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Green
