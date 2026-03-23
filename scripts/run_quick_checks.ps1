param(
  [switch]$SkipCompile,
  [switch]$IncludeVersionGuard,
  [switch]$IncludeHooksGuard,
  [string]$VersionBase = 'HEAD~1',
  [string]$VersionHead = 'HEAD'
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$argsList = @('scripts/run_quick_checks.py')
if ($SkipCompile) { $argsList += '--skip-compile' }
if ($IncludeVersionGuard) {
  $argsList += '--include-version-guard'
  $argsList += '--version-base'
  $argsList += $VersionBase
  $argsList += '--version-head'
  $argsList += $VersionHead
}
if ($IncludeHooksGuard) {
  $argsList += '--include-hooks-guard'
}

python @argsList
exit $LASTEXITCODE
