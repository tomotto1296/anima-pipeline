param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$preCommit = '.githooks/pre-commit'
$prePush = '.githooks/pre-push'

if (-not (Test-Path $preCommit)) {
  Write-Error "[git-hooks] missing $preCommit"
  exit 1
}
if (-not (Test-Path $prePush)) {
  Write-Error "[git-hooks] missing $prePush"
  exit 1
}

if ($DryRun) {
  Write-Host '[git-hooks] dry-run mode (no git config changes)'
} else {
  git config core.hooksPath .githooks
  if ($LASTEXITCODE -ne 0) {
    Write-Error '[git-hooks] failed to set core.hooksPath'
    exit $LASTEXITCODE
  }
}

$hooksPath = (git config --get core.hooksPath).Trim()
if (-not $hooksPath) { $hooksPath = '(unset)' }

if (-not $DryRun -and $hooksPath -ne '.githooks') {
  Write-Error "[git-hooks] unexpected core.hooksPath: $hooksPath"
  exit 1
}

Write-Host "[git-hooks] core.hooksPath=$hooksPath"
Write-Host "[git-hooks] pre-commit: version bump + quick checks を有効化しました"
Write-Host "[git-hooks] pre-push: quick checks (+ version guard + hooks guard) を有効化しました"
