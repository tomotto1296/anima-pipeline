$ErrorActionPreference = 'Stop'

git config core.hooksPath .githooks
Write-Host "[git-hooks] core.hooksPath=.githooks を設定しました"
