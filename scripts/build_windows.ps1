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

Write-Host "Building KeyMuse executable..."
Write-Host "Using Python: $pythonExe"

& $pythonExe -m pip install --quiet pyinstaller

Write-Host "Running PyInstaller..."
& $pythonExe -m PyInstaller --clean -y "$repoRoot\build.spec"

Write-Host ""
Write-Host "Build complete!"
Write-Host "Executable: $repoRoot\dist\KeyMuse.exe"
Write-Host ""
Write-Host "To run the app:"
Write-Host "  .\dist\KeyMuse.exe"
