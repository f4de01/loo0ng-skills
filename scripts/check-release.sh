#!/usr/bin/env bash
# check-release.sh <repo-root>
# 检查发布链是否和上游同构（changesets → version → tag → plugin 版本同步）：
#   - package.json：有 version，scripts.version 里同时含 "changeset version" 与 sync 脚本
#   - .changeset/config.json：存在，privatePackages.version 与 .tag 都为 true，baseBranch 为 main
#   - scripts/sync-plugin-version.mjs 存在
#   - .claude-plugin/plugin.json 的 version 与 package.json 一致
#   - .github/workflows/release.yml 存在，用 changesets/action，version 输入指向 npm run version，publish 为 changeset tag
#   - CHANGELOG.md 存在且含当前版本号
#   - git：当前版本有对应 tag v<version>（提醒级）
#   - 图的 FORMAT_VERSION 与上一个 tag 相比有没有变（提醒级；变了要通知桌面卡片那个仓库）
#   - .gitignore 含 node_modules
# 用法：& "C:\Program Files\Git\bin\bash.exe" assets/check-release.sh <repo-root>
set -u
ROOT="${1:-.}"; ROOT="${ROOT%/}"; ROOT="$(printf '%s' "$ROOT" | tr '\\' '/')"
pass=0; fail=0; warn=0
ok()  { printf '  \033[32m✔\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \033[31m✘\033[0m %s\n' "$1"; fail=$((fail+1)); }
wn()  { printf '  \033[33m!\033[0m %s\n' "$1"; warn=$((warn+1)); }
jget() { grep -m1 -oE "\"$2\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$1" | sed -E 's/.*:[[:space:]]*"([^"]*)"$/\1/'; }

PKG="$ROOT/package.json"; CFG="$ROOT/.changeset/config.json"; PLUGIN="$ROOT/.claude-plugin/plugin.json"
SYNC="$ROOT/scripts/sync-plugin-version.mjs"; WF="$ROOT/.github/workflows/release.yml"; CL="$ROOT/CHANGELOG.md"

echo "package.json"
if [ -f "$PKG" ]; then
  pv="$(jget "$PKG" version)"
  [ -n "$pv" ] && ok "version = $pv" || bad "package.json 缺少 version"
  vs="$(jget "$PKG" version | true)"
  vscript="$(grep -m1 -oE '"version"[[:space:]]*:[[:space:]]*"changeset version[^"]*"' "$PKG" || true)"
  if [ -n "$vscript" ]; then
    ok "scripts.version 以 changeset version 开头"
    printf '%s' "$vscript" | grep -q "sync-plugin-version" && ok "scripts.version 接着运行 sync-plugin-version.mjs" || bad "scripts.version 里没有接 sync-plugin-version.mjs，plugin.json 的版本不会跟着走"
  else
    bad "scripts 里缺少 \"version\": \"changeset version && node scripts/sync-plugin-version.mjs\""
  fi
  grep -q '"@changesets/cli"' "$PKG" && ok "devDependencies 有 @changesets/cli" || bad "没有安装 @changesets/cli（npm install -D @changesets/cli）"
else
  bad "缺少 package.json（版本号的源头）"; pv=""
fi

echo ".changeset/config.json"
if [ -f "$CFG" ]; then
  ok "存在"
  grep -q '"privatePackages"' "$CFG" && grep -A3 '"privatePackages"' "$CFG" | grep -q '"tag"[[:space:]]*:[[:space:]]*true' \
    && ok "privatePackages.tag = true（私有包也打 tag）" \
    || bad "privatePackages.tag 不是 true：package.json 是 private 时 changeset tag 会静默不打任何 tag"
  grep -A3 '"privatePackages"' "$CFG" 2>/dev/null | grep -q '"version"[[:space:]]*:[[:space:]]*true' && ok "privatePackages.version = true" || wn "privatePackages.version 未显式设为 true（当前默认为 true，上游显式写出）"
  grep -q '"baseBranch"[[:space:]]*:[[:space:]]*"main"' "$CFG" && ok "baseBranch = main" || wn "baseBranch 不是 main，要和 release.yml 的分支一致"
  grep -q 'changelog-github' "$CFG" && wn "changelog 用了 @changesets/changelog-github：本地 npm run version 需要 GITHUB_TOKEN 环境变量，否则报错" || ok "changelog 用默认生成器（本地不需要 token）"
else
  bad "缺少 .changeset/config.json（npx changeset init）"
fi

echo "scripts/sync-plugin-version.mjs"
[ -f "$SYNC" ] && ok "存在" || bad "缺少 scripts/sync-plugin-version.mjs"

echo ".claude-plugin/plugin.json"
if [ -f "$PLUGIN" ] && [ -n "$pv" ]; then
  gv="$(jget "$PLUGIN" version)"
  [ "$gv" = "$pv" ] && ok "version 与 package.json 一致（$pv）" || bad "plugin.json 是 $gv，package.json 是 $pv：用户收不到更新（node scripts/sync-plugin-version.mjs）"
else
  bad "缺少 .claude-plugin/plugin.json 或 package.json"
fi

echo ".github/workflows/release.yml"
if [ -f "$WF" ]; then
  ok "存在"
  grep -q 'changesets/action' "$WF" && ok "使用 changesets/action" || bad "没有使用 changesets/action"
  grep -qE 'version:[[:space:]]*npm run version' "$WF" && ok "version 输入 = npm run version（这样 plugin.json 才会同步）" || bad "action 的 version 输入不是 npm run version：Version PR 里 plugin.json 不会被同步"
  grep -qE 'publish:[[:space:]]*npx changeset tag' "$WF" && ok "publish 输入 = npx changeset tag（不发 npm，只打 tag）" || bad "action 的 publish 输入不是 npx changeset tag"
  grep -q 'pull-requests: write' "$WF" && ok "permissions 含 pull-requests: write" || bad "permissions 缺 pull-requests: write，action 开不了 Version PR"
  grep -q 'contents: write' "$WF" && ok "permissions 含 contents: write" || bad "permissions 缺 contents: write，action 推不了分支和 tag"
else
  bad "缺少 .github/workflows/release.yml"
fi

echo "CHANGELOG.md"
if [ -f "$CL" ]; then
  [ -n "$pv" ] && grep -q "^## $pv" "$CL" && ok "含当前版本 $pv 的小节" || wn "CHANGELOG.md 里没有 ## $pv（还没跑过 npm run version？）"
else
  wn "还没有 CHANGELOG.md（第一次 npm run version 后生成）"
fi

echo "git"
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ok "是 git 仓库"
  [ -n "$pv" ] && { git -C "$ROOT" tag | grep -qx "v$pv" && ok "tag v$pv 存在" || wn "还没有 tag v$pv（npx changeset tag 在 version 提交之后运行）"; }
  pending="$(ls "$ROOT/.changeset"/*.md 2>/dev/null | grep -v README.md | wc -l | tr -d ' ')"
  [ "$pending" = 0 ] && ok "没有待消费的 changeset" || wn "有 $pending 个待消费的 changeset（下次 version 会合并进去）"
  [ -f "$ROOT/.gitignore" ] && grep -q node_modules "$ROOT/.gitignore" && ok ".gitignore 含 node_modules" || bad ".gitignore 缺 node_modules（会把依赖提交进仓库）"
else
  bad "不是 git 仓库（git init -b main）"
fi

echo "图的格式版本"
GRAPHPY="$ROOT/skills/engineering/graph/scripts/graph.py"
fv() { grep -m1 -oE '^FORMAT_VERSION[[:space:]]*=[[:space:]]*[0-9]+' "$1" 2>/dev/null | grep -oE '[0-9]+$'; }
if [ -f "$GRAPHPY" ]; then
  now="$(fv "$GRAPHPY")"
  last="$(git -C "$ROOT" tag --sort=-v:refname 2>/dev/null | head -1)"
  if [ -z "$now" ]; then
    bad "graph.py 里读不到 FORMAT_VERSION"
  elif [ -z "$last" ]; then
    wn "还没有 tag，无从比对格式版本（当前 $now）"
  else
    was="$(git -C "$ROOT" show "$last:skills/engineering/graph/scripts/graph.py" 2>/dev/null            | grep -m1 -oE '^FORMAT_VERSION[[:space:]]*=[[:space:]]*[0-9]+' | grep -oE '[0-9]+$')"
    if [ -z "$was" ]; then
      wn "$last 里读不到 FORMAT_VERSION，无从比对（当前 $now）"
    elif [ "$was" = "$now" ]; then
      ok "格式版本与 $last 一致（$now）"
    else
      wn "格式版本从 $was 变成 $now：派生视图的消费方（桌面卡片那个仓库）只认它写死的那一个，发版前通知它"
    fi
  fi
else
  bad "找不到 skills/engineering/graph/scripts/graph.py"
fi

echo
echo "通过 $pass，失败 $fail，提醒 $warn"
[ "$fail" = 0 ]
