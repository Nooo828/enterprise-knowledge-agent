# Run from any directory after authenticating with scripts/gh.ps1.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $accountJson = & (Join-Path $PSScriptRoot 'gh.ps1') api user --jq '{login: .login, id: .id}'
    if ($LASTEXITCODE -ne 0) { throw 'Authenticate with scripts/gh.ps1 auth login first.' }
    $account = $accountJson | ConvertFrom-Json
    $name = git config user.name
    if (-not $name) { git config --local user.name $account.login }
    $email = git config user.email
    if (-not $email) {
        git config --local user.email ($account.id.ToString() + '+' + $account.login + '@users.noreply.github.com')
    }
    $ghPath = Join-Path $projectRoot '.local-tools\gh\bin\gh.exe'
    if (-not (Test-Path -LiteralPath $ghPath)) { $ghPath = (Get-Command gh -ErrorAction Stop).Source }
    $configPath = (Join-Path $projectRoot '.local-tools\gh-config').Replace('\', '/')
    $ghPath = $ghPath.Replace('\', '/')
    # These paths are read by Git's shell; reject shell quote characters.
    if ($configPath.Contains("'") -or $ghPath.Contains("'")) { throw 'Paths containing single quotes are unsupported.' }
    $helper = "!env GH_CONFIG_DIR='" + $configPath + "' '" + $ghPath + "' auth git-credential"
    git config --local --replace-all credential.https://github.com.helper ''
    if ($LASTEXITCODE -ne 0) { throw 'Unable to configure repository credentials.' }
    git config --local --add credential.https://github.com.helper $helper
    if ($LASTEXITCODE -ne 0) { throw 'Unable to configure repository credentials.' }
    Write-Output ('GitHub account configured: ' + $account.login)
    git var GIT_AUTHOR_IDENT
    if ($LASTEXITCODE -ne 0) { throw 'Git author identity is invalid.' }
} finally {
    Pop-Location
}
