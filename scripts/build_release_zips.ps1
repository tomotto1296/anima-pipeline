param(
  [Parameter(Mandatory = $true)]
  [string]$Version,
  [string]$BaseVersion = "1.5.11",
  [string]$DistDir = "dist"
)

$ErrorActionPreference = "Stop"

function New-CleanDirectory {
  param([string]$Path)
  if (Test-Path -LiteralPath $Path) {
    Remove-Item -LiteralPath $Path -Recurse -Force
  }
  New-Item -ItemType Directory -Path $Path | Out-Null
}

function Copy-Items {
  param(
    [string]$Root,
    [string]$Destination,
    [string[]]$Files,
    [string[]]$Dirs
  )

  foreach ($f in $Files) {
    $src = Join-Path $Root $f
    $dst = Join-Path $Destination $f
    $dstParent = Split-Path -Parent $dst
    if (-not (Test-Path -LiteralPath $dstParent)) {
      New-Item -ItemType Directory -Path $dstParent -Force | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
  }

  foreach ($d in $Dirs) {
    $src = Join-Path $Root $d
    $dst = Join-Path $Destination $d
    Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
  }
}

$root = (Resolve-Path ".").Path
$distPath = Join-Path $root $DistDir
if (-not (Test-Path -LiteralPath $distPath)) {
  New-Item -ItemType Directory -Path $distPath | Out-Null
}

$minimalName = "anima-pipeline_v$Version`_minimal"
$upgradeName = "anima-pipeline_v$Version`_upgrade_from_v$BaseVersion"
$minimalDir = Join-Path $distPath $minimalName
$upgradeDir = Join-Path $distPath $upgradeName
$minimalZip = Join-Path $distPath "$minimalName.zip"
$upgradeZip = Join-Path $distPath "$upgradeName.zip"

New-CleanDirectory -Path $minimalDir
New-CleanDirectory -Path $upgradeDir
if (Test-Path -LiteralPath $minimalZip) { Remove-Item -LiteralPath $minimalZip -Force }
if (Test-Path -LiteralPath $upgradeZip) { Remove-Item -LiteralPath $upgradeZip -Force }

# Minimal package: clean install
$minimalFiles = @(
  "anima_pipeline.py",
  "requirements.txt",
  "README.md",
  "README_EN.md",
  "manifest.json",
  "start_anima_pipeline.bat",
  "start_anima_pipeline - Tailscale.bat",
  "frontend/index.html",
  "frontend/i18n.js",
  "docs/guides/anima_pipeline_guide.md",
  "docs/guides/anima_pipeline_guide_en.md",
  "settings/llm_system_prompt.txt",
  "settings/preset_gen_prompt.txt",
  "settings/pipeline_config.default.json",
  "settings/ui_options.json"
)
$minimalDirs = @(
  "core",
  "workflows",
  "chara",
  "presets",
  "assets/icons"
)
Copy-Items -Root $root -Destination $minimalDir -Files $minimalFiles -Dirs $minimalDirs

# Upgrade package: for users already on v1.5.11+
$upgradeFiles = @(
  "anima_pipeline.py",
  "requirements.txt",
  "manifest.json",
  "start_anima_pipeline.bat",
  "start_anima_pipeline - Tailscale.bat",
  "frontend/index.html",
  "frontend/i18n.js",
  "settings/pipeline_config.default.json"
)
$upgradeDirs = @(
  "core",
  "workflows"
)
Copy-Items -Root $root -Destination $upgradeDir -Files $upgradeFiles -Dirs $upgradeDirs

Compress-Archive -Path (Join-Path $minimalDir "*") -DestinationPath $minimalZip -CompressionLevel Optimal
Compress-Archive -Path (Join-Path $upgradeDir "*") -DestinationPath $upgradeZip -CompressionLevel Optimal

Write-Host "Created:"
Write-Host " - $minimalZip"
Write-Host " - $upgradeZip"
