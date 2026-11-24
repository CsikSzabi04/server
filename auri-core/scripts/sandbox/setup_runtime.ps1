# Auri S0 sandbox: dedicated runtime (NO admin needed). Owner: AI-2.
# Copies the base Python (stdlib only, no site-packages) and node.exe to C:\AuriSandbox\runtime,
# so the firewall rule (firewall.ps1) can target these exact binaries.
param([string]$Root = "C:\AuriSandbox\runtime", [string]$PythonHome = "C:\Python312")
$ErrorActionPreference = "Stop"
$py = Join-Path $Root "py"; $nodeDir = Join-Path $Root "node"
New-Item -ItemType Directory -Force $py, $nodeDir | Out-Null
robocopy $PythonHome $py /E /NFL /NDL /NJH /NJS /XD site-packages Scripts Doc tcl include libs __pycache__ test idlelib turtledemo | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
Copy-Item (Get-Command node.exe).Source (Join-Path $nodeDir "node.exe") -Force
& (Join-Path $py "python.exe") -I -c "import sys, unittest; print('python', sys.version.split()[0], 'OK')"
& (Join-Path $nodeDir "node.exe") -e "console.log('node', process.version, 'OK')"
Write-Host "Kész: $Root"
