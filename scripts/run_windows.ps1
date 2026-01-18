# Run KeyMuse - unified speech-to-text app
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

$env:PYTHONPATH = @(
    "$repoRoot\shared\src",
    "$repoRoot\backend\src",
    "$repoRoot\client\src"
) -join ";"

if (-not $env:HF_HOME) {
    $env:HF_HOME = "$repoRoot\.hf_cache"
}

# Find Python - prefer project venv
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} elseif ($env:VIRTUAL_ENV) {
    $pythonExe = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} else {
    $pythonExe = "python"
}

# Run the unified app
& $pythonExe -m keymuse_client.launcher @args
