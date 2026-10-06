param([string]$OutputDirectory = 'results/local')
$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try {
    python scripts/tc0.py --output $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw 'TC-0 experiment failed' }
} finally { Pop-Location }
