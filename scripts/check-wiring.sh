#!/usr/bin/env bash
# check-wiring.sh <repo-root>
# 检查 promoted 接线是否完整（对应上游 CLAUDE.md 的不变量）：
#   promoted skill（engineering/、productivity/）必须：
#     - 顶层 README.md 里有链接 ./skills/<bucket>/<name>/SKILL.md
#     - bucket README.md 里有链接 ./<name>/SKILL.md
#     - .claude-plugin/plugin.json 的 skills 数组里有 "./skills/<bucket>/<name>"
#     - docs/<bucket>/<name>.md 存在
#   非 promoted skill（misc/、in-progress/、deprecated/）必须：
#     - 出现在自己 bucket 的 README.md 里
#     - 不出现在顶层 README.md、plugin.json，且没有 docs 页
#   plugin.json 里的每个路径都必须指向一个存在的 SKILL.md
# 用法：& "C:\Program Files\Git\bin\bash.exe" assets/check-wiring.sh <repo-root>
set -u
ROOT="${1:-.}"; ROOT="${ROOT%/}"; ROOT="$(printf '%s' "$ROOT" | tr '\\' '/')"
pass=0; fail=0; warn=0
ok()  { printf '  \033[32m✔\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \033[31m✘\033[0m %s\n' "$1"; fail=$((fail+1)); }
wn()  { printf '  \033[33m!\033[0m %s\n' "$1"; warn=$((warn+1)); }

[ -d "$ROOT/skills" ] || { echo "找不到 $ROOT/skills"; exit 1; }
README="$ROOT/README.md"; PLUGIN="$ROOT/.claude-plugin/plugin.json"

echo "仓库级文件"
[ -f "$README" ] && ok "README.md 存在" || bad "缺少顶层 README.md"
if [ -f "$PLUGIN" ]; then
  ok ".claude-plugin/plugin.json 存在"
  grep -q '"skills"' "$PLUGIN" && ok "plugin.json 有 skills 数组" || bad "plugin.json 缺少 \"skills\" 数组（上游用显式路径数组列出 promoted skill）"
  grep -q '"version"' "$PLUGIN" && ok "plugin.json 有 version（用户只有在它变化时才收到更新）" || wn "plugin.json 没有 version 字段，用户将无法按版本收到更新"
  if [ -f "$ROOT/package.json" ]; then
    pv="$(grep -m1 -oE '"version"[[:space:]]*:[[:space:]]*"[^"]+"' "$ROOT/package.json" | sed -E 's/.*"([^"]+)"$/\1/')"
    gv="$(grep -m1 -oE '"version"[[:space:]]*:[[:space:]]*"[^"]+"' "$PLUGIN" | sed -E 's/.*"([^"]+)"$/\1/')"
    [ "$pv" = "$gv" ] && ok "package.json 与 plugin.json 版本一致（$pv）" || bad "package.json 版本 $pv 与 plugin.json 版本 $gv 不一致（上游用 scripts/sync-plugin-version.mjs 同步）"
  fi
  # 每个 plugin.json 路径都要指向真实 SKILL.md
  grep -oE '"\./skills/[^"]+"' "$PLUGIN" | tr -d '"' | while read -r p; do
    [ -f "$ROOT/${p#./}/SKILL.md" ] || printf '  \033[31m✘\033[0m plugin.json 指向的 %s 下没有 SKILL.md\n' "$p"
  done
else
  bad "缺少 .claude-plugin/plugin.json（Claude Code plugin 清单）"
fi
[ -f "$ROOT/CLAUDE.md" ] && ok "CLAUDE.md 存在（仓库不变量写在这里）" || wn "没有 CLAUDE.md：上游把 bucket 规则与接线清单写在这里，agent 才会遵守"

for bucket_dir in "$ROOT"/skills/*/; do
  bucket="$(basename "$bucket_dir")"
  BR="$bucket_dir/README.md"
  case "$bucket" in engineering|productivity) promoted=1 ;; *) promoted=0 ;; esac
  for sd in "$bucket_dir"*/; do
    [ -f "$sd/SKILL.md" ] || continue
    name="$(basename "$sd")"
    echo "skills/$bucket/$name（$([ $promoted = 1 ] && echo promoted || echo 非 promoted)）"
    if [ -f "$BR" ]; then
      grep -qF "(./$name/SKILL.md)" "$BR" && ok "bucket README 链接了 ./$name/SKILL.md" || bad "skills/$bucket/README.md 里没有 (./$name/SKILL.md) 链接"
    else
      bad "缺少 skills/$bucket/README.md（每个 bucket 都要有）"
    fi
    in_readme=0; in_plugin=0; has_docs=0
    [ -f "$README" ] && grep -qF "(./skills/$bucket/$name/SKILL.md)" "$README" && in_readme=1
    [ -f "$PLUGIN" ] && grep -qF "\"./skills/$bucket/$name\"" "$PLUGIN" && in_plugin=1
    [ -f "$ROOT/docs/$bucket/$name.md" ] && has_docs=1
    if [ $promoted = 1 ]; then
      [ $in_readme = 1 ] && ok "顶层 README 链接了它" || bad "顶层 README.md 缺少 (./skills/$bucket/$name/SKILL.md)"
      [ $in_plugin = 1 ] && ok "plugin.json 列出了它" || bad "plugin.json 的 skills 数组缺少 \"./skills/$bucket/$name\""
      [ $has_docs = 1 ] && ok "docs/$bucket/$name.md 存在" || bad "缺少 docs/$bucket/$name.md"
      if [ $has_docs = 1 ]; then
        for h in "## What it does" "## When to reach for it" "## Where it fits"; do
          grep -qF "$h" "$ROOT/docs/$bucket/$name.md" || wn "docs/$bucket/$name.md 缺少固定小节 \"$h\""
        done
      fi
    else
      [ $in_readme = 0 ] && ok "顶层 README 没有它（正确）" || bad "非 promoted 的 skill 不该出现在顶层 README.md"
      [ $in_plugin = 0 ] && ok "plugin.json 没有它（正确）" || bad "非 promoted 的 skill 不该进 plugin.json"
      [ $has_docs = 0 ] && ok "没有 docs 页（正确）" || bad "非 promoted 的 skill 不该有 docs 页"
    fi
  done
done

echo
echo "通过 $pass，失败 $fail，提醒 $warn"
[ "$fail" = 0 ]
