#!/usr/bin/env bash
# check-stale.sh <repo-root> <old-skill-name>
# 改名或退役一个 skill 之后，找出仓库里所有仍然提到旧名字的地方。
# 允许出现旧名字的文件：CHANGELOG.md、.changeset/*.md（它们本来就该记录旧名）、.git、node_modules。
# 其余任何地方（README、bucket README、plugin.json、docs、router skill、CLAUDE.md、其他 SKILL.md）出现即失败。
# 用法：& "C:\Program Files\Git\bin\bash.exe" assets/check-stale.sh <repo-root> summarise-diff
set -u
ROOT="${1:-.}"; ROOT="${ROOT%/}"; ROOT="$(printf '%s' "$ROOT" | tr '\\' '/')"
OLD="${2:-}"
[ -n "$OLD" ] || { echo "用法: check-stale.sh <repo-root> <old-skill-name>"; exit 2; }
cd "$ROOT" || exit 2

echo "在 $ROOT 里查找旧名字 \"$OLD\"（排除 CHANGELOG.md、.changeset/、.git、node_modules）"
hits="$(grep -rn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.changeset --exclude=CHANGELOG.md -F "$OLD" . 2>/dev/null || true)"
if [ -d "skills" ] && find skills -type d -name "$OLD" | grep -q .; then
  printf '  \033[31m✘\033[0m 目录仍然存在: %s\n' "$(find skills -type d -name "$OLD")"
  dir_hit=1
else
  printf '  \033[32m✔\033[0m 没有名为 %s 的 skill 目录\n' "$OLD"
  dir_hit=0
fi
doc_hits="$(printf '%s\n' "$hits" | grep -E '^\./docs/' || true)"
other_hits="$(printf '%s\n' "$hits" | grep -vE '^\./docs/' || true)"
if [ -n "$doc_hits" ]; then
  printf '  \033[33m!\033[0m docs 页里提到旧名字（上游允许：新 skill 的 docs 页用 "Where did X go?" 回答改名，确认是有意为之）:\n'
  printf '%s\n' "$doc_hits" | sed 's/^/      /'
fi
if [ -n "$other_hits" ]; then
  printf '  \033[31m✘\033[0m 以下位置仍提到旧名字（必须改掉）:\n'
  printf '%s\n' "$other_hits" | sed 's/^/      /'
  n="$(printf '%s\n' "$other_hits" | wc -l | tr -d ' ')"
  echo; echo "失败：$n 处残留引用 + $dir_hit 个目录"
  exit 1
fi
[ -z "$doc_hits" ] && printf '  \033[32m✔\033[0m 没有残留引用\n'
echo; [ "$dir_hit" = 0 ] && { echo "通过"; exit 0; } || { echo "失败：目录未删除"; exit 1; }
