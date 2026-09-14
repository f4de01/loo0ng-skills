# 开发者本机用：把仓库 skills/<bucket>/<name>/ 逐条以 junction 挂到两个 harness 的用户级 skill 目录（Matt 分桶，链接名只取 <name>）。
#   ~/.claude/skills/<name>  Claude Code
#   ~/.agents/skills/<name>  Codex 及其他 Agent Skills 兼容 harness
# junction 不需要管理员权限或开发者模式。junction 指向目录，改 skill 内容即时生效（Claude Code 热加载）；
# 只在改名、增删 skill 后重跑。幂等：重跑结果一致；skills/ 里已不存在的 skill，其指向本仓库的 junction 随之删除。
# 照上游 link-skills.sh：deprecated/ 与 misc/ 两个桶不挂（退役的与不推广的都不该进日常目录），in-progress/ 照挂。
# 不是安装器；律师机器上的安装走插件或 skills.sh。
# 本文件须带 UTF-8 BOM：Windows PowerShell 5.1 无 BOM 时按 ANSI 读，中文注释会撕坏语法。
# -Repo 与 -Dests 只供测试指向临时目录（tests/link-skills/），日常直接跑不带参数。
param(
  [string]$Repo = '',
  [string[]]$Dests = @()
)
$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }
if ($Dests.Count -eq 0) { $Dests = @((Join-Path $HOME '.claude\skills'), (Join-Path $HOME '.agents\skills')) }
$Repo = (Resolve-Path $Repo).Path
git -C $Repo config core.hooksPath .githooks   # 隐私钩子（ADR-0014）：.githooks/ 里的 pre-commit 与 commit-msg
$skillsRoot = Join-Path $Repo 'skills'

$srcs = @()
if (Test-Path $skillsRoot) {
  $srcs = @(Get-ChildItem -Path $skillsRoot -Recurse -Filter 'SKILL.md' -File |
    Where-Object { ($_.FullName -notlike '*\node_modules\*') -and ($_.FullName -notlike '*\deprecated\*') } |
    ForEach-Object { $_.Directory })
}
$names = @($srcs | ForEach-Object { $_.Name })

function Get-LinkTarget($item) {
  $t = $item.Target
  if ($t -is [array]) { $t = $t[0] }
  return [string]$t
}

function Remove-Link($item) {
  $item.Delete()   # 只删链接本身，不进目标
}

foreach ($dest in $Dests) {
  if ((Test-Path $dest) -and ((Get-Item $dest -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    $target = Get-LinkTarget (Get-Item $dest -Force)
    if ($target -and ($target -like "$Repo*")) {
      throw "$dest 是指向本仓库的链接（$target），先删掉再重跑。"
    }
  }
  New-Item -ItemType Directory -Force -Path $dest | Out-Null

  # 清掉指向本仓库 skills/ 但源目录已不存在（或已改名）的 junction；别处来的条目一律不碰。
  foreach ($item in Get-ChildItem -Path $dest -Force -Directory) {
    if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
    $target = Get-LinkTarget $item
    if (-not $target) { continue }
    if (($target -like "$skillsRoot\*") -and ($names -notcontains $item.Name)) {
      Remove-Link $item
      Write-Output "unlinked $($item.Name) ($dest)"
    }
  }

  foreach ($src in $srcs) {
    $name = $src.Name
    $link = Join-Path $dest $name
    if (Test-Path $link) {
      $item = Get-Item $link -Force
      if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Remove-Link $item
      } else {
        Remove-Item $link -Recurse -Force
      }
    }
    New-Item -ItemType Junction -Path $link -Target $src.FullName | Out-Null
    Write-Output "linked $name -> $($src.FullName) ($dest)"
  }
}
