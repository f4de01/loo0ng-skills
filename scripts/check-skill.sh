#!/usr/bin/env bash
# check-skill.sh <repo-root>
# 检查一个 skill 仓库里的每个 skill 目录是否满足 mattpocock/skills 的约定：
#   - skills/<bucket>/<name>/SKILL.md 存在，frontmatter 合法
#   - name 与目录名一致，且符合 Agent Skills 规范（小写字母数字连字符，<=64）
#   - description 非空、<=1024 字符、含 ": " 时必须加引号（上游 #907 的坑）
#   - agents/openai.yaml 存在，含 interface.display_name / short_description
#   - user-invoked 两端一致：disable-model-invocation: true <=> policy.allow_implicit_invocation: false
#   - skill 直接子目录只允许 agents/、scripts/、assets/，只有 assets/ 可嵌套
#   - SKILL.md 正文的参考指针不能指向 assets/ 数据
#   - 正文随包自足：skill 根目录的全部 *.md 里不出现 ADR 号、issue 号、版本号，
#     也不指向本 skill 目录之外的仓库文件（装到用户机上的 skill 读不到那些东西）
# 用法示例：bash assets/check-skill.sh ~/my-skills
set -u
ROOT="${1:-.}"
ROOT="${ROOT%/}"
CHECKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python
pass=0; fail=0; warn=0
ok()  { printf '  \033[32m✔\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \033[31m✘\033[0m %s\n' "$1"; fail=$((fail+1)); }
wn()  { printf '  \033[33m!\033[0m %s\n' "$1"; warn=$((warn+1)); }

ROOT="$(printf '%s' "$ROOT" | tr '\\' '/')"           # 允许传 Windows 路径
if [ ! -d "$ROOT/skills" ] && [ "$(basename "$ROOT")" = "skills" ]; then
  ROOT="$(dirname "$ROOT")"                            # 传的是 skills/ 本身也接受
fi
if [ ! -d "$ROOT/skills" ]; then
  echo "找不到 $ROOT/skills 目录。skill 仓库的根下应有 skills/<bucket>/<name>/SKILL.md"
  exit 1
fi

# 正文随包自足要拦下的东西：ADR 号、`#` 加数字形的 issue 号、版本号、包外仓库文件与只在仓库里成立的约定名。
SELF_CONTAINED_BAN='ADR-?[0-9]|(^|[^A-Za-z0-9])#[0-9]|[0-9]+\.[0-9]+\.[0-9]+|CONTEXT\.md|CHANGELOG|\.changeset|(^|[^A-Za-z0-9_./-])(docs|tests|skills)/|结构不变量|硬边界'

fm_get() { printf '%s\n' "$FM" | grep -m1 -E "^$1:" | sed -E "s/^$1:[[:space:]]*//"; }
unquote() { printf '%s' "$1" | sed -E 's/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/'; }

found=0
while IFS= read -r -d '' skill_md; do
  found=1
  dir="$(dirname "$skill_md")"
  name_dir="$(basename "$dir")"
  bucket="$(basename "$(dirname "$dir")")"
  echo "${dir#"$ROOT"/}"

  layout_ok=1
  while IFS= read -r -d '' child; do
    case "$(basename "$child")" in
      assets) ;;
      agents|scripts)
        while IFS= read -r -d '' nested; do
          bad "只有 assets 可嵌套目录：${nested#"$ROOT"/}"; layout_ok=0
        done < <(find "$child" -mindepth 1 -type d -print0)
        ;;
      *) bad "不允许的 skill 子目录：${child#"$ROOT"/}"; layout_ok=0 ;;
    esac
  done < <(find "$dir" -mindepth 1 -maxdepth 1 -type d -print0)
  [ "$layout_ok" = 0 ] || ok "skill 子目录布局合法"

  if pointer_hits="$("$PYTHON" "$CHECKER_DIR/check-asset-pointers.py" "$skill_md" 2>&1)"; then
    ok "正文参考指针与数据分离"
  else
    bad "$pointer_hits"
  fi

  if [ "$(basename "$skill_md")" != "SKILL.md" ]; then
    bad "文件名必须是大写的 SKILL.md（现在是 $(basename "$skill_md")）。Windows 不分大小写，但 Linux/macOS 上的 harness 会找不到它"
  fi
  if [ "$(head -n1 "$skill_md")" != "---" ]; then
    bad "SKILL.md 第一行必须是 ---（frontmatter 起始）"
    continue
  fi
  FM="$(awk 'NR==1{next} /^---[ \t]*$/{exit} {print}' "$skill_md")"

  case "$bucket" in
    engineering|productivity|misc|in-progress|deprecated) ok "bucket 为 $bucket" ;;
    *) wn "bucket \"$bucket\" 不是上游五个 bucket 之一（engineering/productivity/misc/in-progress/deprecated）" ;;
  esac

  raw_name="$(fm_get name)"; fm_name="$(unquote "$raw_name")"
  if [ -z "$fm_name" ]; then bad "frontmatter 缺少 name"
  elif [ "$fm_name" != "$name_dir" ]; then bad "name: $fm_name 与目录名 $name_dir 不一致"
  elif ! printf '%s' "$fm_name" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then bad "name 只能用小写字母、数字、单个连字符（Agent Skills 规范）"
  elif [ "${#fm_name}" -gt 64 ]; then bad "name 超过 64 字符"
  else ok "name 与目录名一致且合法"; fi

  raw_desc="$(fm_get description)"; desc="$(unquote "$raw_desc")"
  if [ -z "$desc" ]; then bad "frontmatter 缺少 description"
  elif [ "${#desc}" -gt 1024 ]; then bad "description 超过 1024 字符（规范上限）"
  else
    case "$raw_desc" in
      \"*|\'*) ok "description 非空且已加引号" ;;
      *) if printf '%s' "$raw_desc" | grep -q ': '; then
           bad "description 含未加引号的 ': '，YAML 会解析失败，skills.sh 会跳过这个 skill（上游 #907）"
         else ok "description 非空"; fi ;;
    esac
  fi

  printf '%s\n' "$FM" | grep -oE '^[A-Za-z-]+:' | sed 's/:$//' | while read -r key; do
    case "$key" in
      name|description|disable-model-invocation|argument-hint) ;;
      *) printf '  \033[33m!\033[0m 字段 %s 不在上游使用的四个字段之内（name/description/disable-model-invocation/argument-hint），确认是有意为之\n' "$key" ;;
    esac
  done

  dmi="$(fm_get disable-model-invocation)"
  yaml="$dir/agents/openai.yaml"
  if [ ! -f "$yaml" ]; then
    bad "缺少 agents/openai.yaml（Codex 侧元数据，上游每个 skill 都带）"
  else
    grep -qE '^\s*display_name:' "$yaml" && grep -qE '^\s*short_description:' "$yaml" \
      && ok "agents/openai.yaml 含 display_name 与 short_description" \
      || bad "agents/openai.yaml 缺少 interface.display_name 或 short_description"
    if grep -qE '^\s*allow_implicit_invocation:\s*false' "$yaml"; then aif=1; else aif=0; fi
    if [ "$dmi" = "true" ] && [ "$aif" = 1 ]; then ok "user-invoked：两个 harness 一致"
    elif [ "$dmi" != "true" ] && [ "$aif" = 0 ]; then ok "model-invoked：两个 harness 一致"
    elif [ "$dmi" = "true" ]; then bad "Claude 侧是 user-invoked，但 openai.yaml 缺 policy.allow_implicit_invocation: false"
    else bad "openai.yaml 是 user-invoked，但 SKILL.md 缺 disable-model-invocation: true"; fi
  fi

  # 正文随包自足：装到用户机上的每一件 skill 自己说完该说的，不指向它读不到的东西。
  # 先剥白名单再扫：清单坐标（p2#1）、指向本 skill 兄弟文件的链接、钉住的后端版本号。
  self_hits=""
  for doc in "$dir"/*.md; do
    [ -f "$doc" ] || continue
    h="$(sed -E \
           -e 's/p[0-9]+#[0-9]+//g' \
           -e 's#\]\((\./)?[A-Za-z0-9_-]+\.[A-Za-z0-9]+\)#]#g' \
           -e 's/python-docx[ =]*[0-9]+(\.[0-9]+)+//g' \
           -e 's/python ?[0-9]+(\.[0-9]+)+//g' \
           "$doc" \
         | grep -nE "$SELF_CONTAINED_BAN" | head -3)"
    [ -n "$h" ] && self_hits="$self_hits $(basename "$doc"):$(printf '%s' "$h" | cut -d: -f1 | tr '\n' ',')"
  done
  if [ -n "$self_hits" ]; then
    bad "正文不随包自足：还留着 ADR 号、issue 号、版本号或包外仓库引用（文件:行）$self_hits"
  else
    ok "正文随包自足"
  fi

done < <(find "$ROOT/skills" -mindepth 3 -maxdepth 3 -iname SKILL.md -print0 | sort -z)

[ "$found" = 1 ] || { echo "skills/ 下没有任何 SKILL.md"; exit 1; }
echo
echo "通过 $pass，失败 $fail，提醒 $warn"
[ "$fail" = 0 ]
