# Use the verified, project-local GitHub CLI without changing the system PATH.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$ghPath = Join-Path $projectRoot '.local-tools\gh\bin\gh.exe'
if (-not (Test-Path -LiteralPath $ghPath)) {
    $installedGh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $installedGh) {
        throw 'GitHub CLI is missing. See docs/06-github-delivery.md.'
    }
    $ghPath = $installedGh.Source
}
$previousConfig = $env:GH_CONFIG_DIR
try {
    $env:GH_CONFIG_DIR = Join-Path $projectRoot '.local-tools\gh-config'
    & $ghPath @args
    $result = $LASTEXITCODE
} finally {
    $env:GH_CONFIG_DIR = $previousConfig
}
exit $result
