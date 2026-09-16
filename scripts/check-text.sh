#!/usr/bin/env bash
# check-text.sh <repo-root>
# 全仓文本规矩的机械守门。这三条本来只以命令的形态写在 docs/agents/skills.md「其他检查」里，
# 没有任何脚本查它，全靠人记得跑，于是破折号一路漂到 14 个文件 68 处才被发现。
#   1. 全仓禁破折号 U+2014。连接号 U+2013 用于数字区间，不在此列，一个都不许顺手换掉。
#      正则里真要认这个字符时写成 \u2014 转义（Python re 认得），别在源码里放字面字符。
#   2. .ps1 以外的文本文件不得带 UTF-8 BOM：带 BOM 的 SKILL.md 会让 Codex 静默跳过整个根目录。
#   3. 每个 .ps1 必须带 UTF-8 BOM：PowerShell 5.1 不带 BOM 时按 ANSI 读，中文注释会撕坏语法。
# 名单取自 git ls-files，所以只扫进了版本库的文件；二进制由 grep -I 自己跳过。
# 用法：bash scripts/check-text.sh <repo-root>
set -u
ROOT="${1:-.}"; ROOT="${ROOT%/}"; ROOT="$(printf '%s' "$ROOT" | tr '\\' '/')"
pass=0; fail=0
ok()  { printf '  \033[32m✔\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \033[31m✘\033[0m %s\n' "$1"; fail=$((fail+1)); }

cd "$ROOT" || { echo "进不去 $ROOT"; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "$ROOT 不是 git 仓库（名单取自 git ls-files）"; exit 2; }

echo "全仓文本规矩"

# 1. 破折号 U+2014
hits="$(git ls-files -z | xargs -0 grep -c -I -P '\x{2014}' 2>/dev/null | grep -v ':0$' || true)"
if [ -z "$hits" ]; then
  ok "没有破折号 U+2014（连接号 U+2013 不在此列）"
else
  bad "有文件带破折号 U+2014，逐个改掉（文件:命中行数）："
  printf '%s\n' "$hits" | sed 's/^/      /'
fi

# 2. .ps1 以外不得带 BOM
bom="$(git ls-files -z | grep -z -v '\.ps1$' | xargs -0 grep -l -I "$(printf '^\xEF\xBB\xBF')" 2>/dev/null || true)"
if [ -z "$bom" ]; then
  ok ".ps1 以外的文本文件都不带 BOM"
else
  bad "这些文件带了 UTF-8 BOM，去掉："
  printf '%s\n' "$bom" | sed 's/^/      /'
fi

# 3. .ps1 必须带 BOM
# 用 -z 读：git ls-files 默认把非 ASCII 路径加引号转义，按行读会读到一个打不开的名字，
# 那种 .ps1 就被静默跳过、检查假绿。
missing=""
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  head_bytes="$(head -c 3 "$f" | od -An -tx1 | tr -d ' \n')"
  [ "$head_bytes" = "efbbbf" ] || missing="$missing$f"$'\n'
done < <(git ls-files -z '*.ps1')
if [ -z "$missing" ]; then
  ok "每个 .ps1 都带 UTF-8 BOM"
else
  bad "这些 .ps1 没带 UTF-8 BOM（PowerShell 5.1 会按 ANSI 读，中文注释撕坏语法）："
  printf '%s' "$missing" | sed 's/^/      /'
fi

echo
echo "通过 $pass，失败 $fail"
[ "$fail" = 0 ]
