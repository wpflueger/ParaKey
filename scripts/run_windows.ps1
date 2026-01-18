$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

$env:PYTHONPATH = @(
    "$repoRoot\shared\src",
    "$repoRoot\backend\src",
    "$repoRoot\client\src"
) -join ";"

py -3.11 -m keymuse_client.launcher
