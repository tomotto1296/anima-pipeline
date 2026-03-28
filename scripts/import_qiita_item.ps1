param(
  [Parameter(Mandatory = $true)]
  [string]$ItemId,
  [Parameter(Mandatory = $true)]
  [string]$OutputDir
)

$ErrorActionPreference = "Stop"

$item = Invoke-RestMethod -Method Get -Uri "https://qiita.com/api/v2/items/$ItemId"

$safeTitle = $item.title -replace '"', '\"'
$private = [string]$item.private
$private = $private.ToLower()
$slide = [string]$item.slide
$slide = $slide.ToLower()
$org = if ([string]::IsNullOrEmpty($item.organization_url_name)) { "null" } else { $item.organization_url_name }
$tags = ($item.tags | ForEach-Object { "  - $($_.name)" }) -join "`r`n"

$header = @"
---
title: "$safeTitle"
tags:
$tags
private: $private
updated_at: '$($item.updated_at)'
id: $($item.id)
organization_url_name: $org
slide: $slide
ignorePublish: false
---
"@

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$outPath = Join-Path $OutputDir "$ItemId.md"
Set-Content -LiteralPath $outPath -Value ($header + "`r`n" + $item.body) -Encoding UTF8
Write-Output "Imported: $outPath"
