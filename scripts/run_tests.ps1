$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

$env:PYTHONPATH = @(
    "$repoRoot\shared\src",
    "$repoRoot\backend\src",
    "$repoRoot\client\src"
) -join ";"

$pythonExe = if ($env:VIRTUAL_ENV) {
    Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} else {
    (Get-Command python -ErrorAction Stop).Source
}

& $pythonExe -m pytest -v backend\tests client\tests
