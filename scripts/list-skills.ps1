# 列出全仓 SKILL.md 的相对路径，排除 node_modules，按路径排序。
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Get-ChildItem -LiteralPath $repo -Recurse -Force -File -Filter 'SKILL.md' |
  Where-Object { $_.FullName -notlike '*\node_modules\*' } |
  ForEach-Object { $_.FullName.Substring($repo.Length + 1).Replace('\', '/') } |
  Sort-Object
