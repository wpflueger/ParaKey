$ErrorActionPreference = "Stop"

$buildStart = Get-Date

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

$env:PYTHONPATH = @(
    "$repoRoot\shared\src",
    "$repoRoot\backend\src",
    "$repoRoot\client\src"
) -join ";"

# Use project venv if it exists, otherwise fall back to system Python
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} elseif ($env:VIRTUAL_ENV) {
    $pythonExe = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} else {
    $pythonExe = "py"
}

Write-Host "Building KeyMuse executable..."
Write-Host "Using Python: $pythonExe"
Write-Host ""

# Check if pyinstaller is installed
$stepStart = Get-Date
Write-Host "[1/2] Checking PyInstaller..."
try {
    & $pythonExe -c "import PyInstaller" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "not installed" }
} catch {
    Write-Host "      Installing PyInstaller..."
    & $pythonExe -m pip install --quiet pyinstaller
}
$stepTime = (Get-Date) - $stepStart
Write-Host "      Done ($([math]::Round($stepTime.TotalSeconds, 1))s)"
Write-Host ""

# Run PyInstaller (no --clean to use cache for faster rebuilds)
$stepStart = Get-Date
Write-Host "[2/2] Running PyInstaller..."
Push-Location $repoRoot
try {
    & $pythonExe -m PyInstaller -y "$repoRoot\build.spec"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed!" -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}
$stepTime = (Get-Date) - $stepStart
Write-Host "      Done ($([math]::Round($stepTime.TotalSeconds, 1))s)"
Write-Host ""

$totalTime = (Get-Date) - $buildStart
Write-Host "========================================" -ForegroundColor Green
Write-Host "Build complete in $([math]::Round($totalTime.TotalSeconds, 1))s" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Executable: $repoRoot\dist\KeyMuse\KeyMuse.exe"
Write-Host ""
Write-Host "To run: .\dist\KeyMuse\KeyMuse.exe"
