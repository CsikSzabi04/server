# Auri S0 sandbox: block OUTBOUND network for the dedicated runtime. Run ONCE as Administrator. Owner: AI-2.
#   powershell -ExecutionPolicy Bypass -File firewall.ps1           # add / refresh the rules
#   powershell -ExecutionPolicy Bypass -File firewall.ps1 -Remove   # remove them
param([string]$Root = "C:\AuriSandbox\runtime", [switch]$Remove)
$ErrorActionPreference = "Stop"
$rules = @{ "Auri sandbox python" = (Join-Path $Root "py\python.exe"); "Auri sandbox node" = (Join-Path $Root "node\node.exe") }
foreach ($name in $rules.Keys) {
    Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    if ($Remove) { Write-Host "Törölve: $name"; continue }
    if (-not (Test-Path $rules[$name])) { throw "Hiányzik: $($rules[$name]) - előbb futtasd a setup_runtime.ps1-et" }
    New-NetFirewallRule -DisplayName $name -Direction Outbound -Action Block -Program $rules[$name] -Profile Any | Out-Null
    Write-Host "Kimenő forgalom tiltva: $($rules[$name])"
}
