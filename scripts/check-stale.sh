#!/usr/bin/env bash
# check-stale.sh <repo-root> <old-skill-name>
# 改名或退役一个 skill 之后，找出仓库里所有仍然提到旧名字的地方。
# 允许出现旧名字的文件：CHANGELOG.md、.changeset/*.md（它们本来就该记录旧名）。
# 其余任何地方（README、bucket README、plugin.json、docs、router skill、CLAUDE.md、其他 SKILL.md）出现即失败。
# 名单是「已跟踪 + 未被忽略的未跟踪」，问 git 要，与 check-text.sh、check-skill.sh 同一条口径：
# 原先这里手写着一份 --exclude-dir 名单（.git、node_modules、__pycache__），它与 .gitignore
# 各走各的，迟早分叉；被忽略的产物本来就不该算残留引用。真不想被扫的东西该进 .gitignore。
# 传进来的目录不是 git 仓库就退 2：名单只有 git 列得出，这个脚本也只在仓库里有意义
# （扫任意 skill 仓库的是 check-skill.sh，那边探不到 git 就照旧全扫）。
# 用法：& "C:\Program Files\Git\bin\bash.exe" scripts/check-stale.sh <repo-root> summarise-diff
set -u
ROOT="${1:-.}"; ROOT="${ROOT%/}"; ROOT="$(printf '%s' "$ROOT" | tr '\\' '/')"
OLD="${2:-}"
[ -n "$OLD" ] || { echo "用法: check-stale.sh <repo-root> <old-skill-name>"; exit 2; }
cd "$ROOT" || exit 2
git rev-parse --git-dir >/dev/null 2>&1 || { echo "$ROOT 不是 git 仓库（名单要靠 git 列）"; exit 2; }

# 两个名单互斥，接在一起即可。全程 -z：git ls-files 默认把非 ASCII 路径加引号转义，
# 按行读会读到一个打不开的名字，而这个仓库的路径大量是中文。
# 语义上的例外（CHANGELOG.md、.changeset/）与「被忽略」无关，在这里单独滤掉。
files_z() {
  { git ls-files -z; git ls-files -z --others --exclude-standard; } \
    | grep -z -vE '(^|/)CHANGELOG\.md$|(^|/)\.changeset/'
}

echo "在 $ROOT 里查找旧名字 \"$OLD\"（排除 CHANGELOG.md、.changeset/，以及被 .gitignore 忽略的）"
# -H 不能省：xargs 分批之后某一批可能只剩一个文件，grep 那时不打文件名，命中行就读不出在哪儿。
hits="$(files_z | xargs -0 grep -nHI -F "$OLD" 2>/dev/null || true)"
dirs=""
while IFS= read -r -d '' d; do
  git check-ignore -q "$d" && continue   # 被忽略的产物目录不算残留（退出码 1 是没命中，128 才是出错）
  dirs="$dirs$d"$'\n'
done < <([ -d skills ] && find skills -type d -name "$OLD" -print0)
if [ -n "$dirs" ]; then
  printf '  \033[31m✘\033[0m 目录仍然存在: %s\n' "$(printf '%s' "$dirs" | tr '\n' ' ' | sed 's/ *$//')"
  dir_hit=1
else
  printf '  \033[32m✔\033[0m 没有名为 %s 的 skill 目录\n' "$OLD"
  dir_hit=0
fi
doc_hits="$(printf '%s\n' "$hits" | grep -E '^docs/' || true)"
other_hits="$(printf '%s\n' "$hits" | grep -vE '^docs/' || true)"
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
