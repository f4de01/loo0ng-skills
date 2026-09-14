#!/usr/bin/env bash
# check-skill.sh <repo-root>
# 检查一个 skill 仓库里的每个 skill 目录是否满足 mattpocock/skills 的约定：
#   - skills/<bucket>/<name>/SKILL.md 存在，frontmatter 合法
#   - name 与目录名一致，且符合 Agent Skills 规范（小写字母数字连字符，<=64）
#   - description 非空、<=1024 字符、含 ": " 时必须加引号（上游 #907 的坑）
#   - agents/openai.yaml 存在，含 interface.display_name / short_description
#   - user-invoked 两端一致：disable-model-invocation: true <=> policy.allow_implicit_invocation: false
# 用法示例：bash assets/check-skill.sh ~/my-skills
set -u
ROOT="${1:-.}"
ROOT="${ROOT%/}"
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

fm_get() { printf '%s\n' "$FM" | grep -m1 -E "^$1:" | sed -E "s/^$1:[[:space:]]*//"; }
unquote() { printf '%s' "$1" | sed -E 's/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/'; }

found=0
while IFS= read -r -d '' skill_md; do
  found=1
  dir="$(dirname "$skill_md")"
  name_dir="$(basename "$dir")"
  bucket="$(basename "$(dirname "$dir")")"
  echo "${dir#"$ROOT"/}"

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
done < <(find "$ROOT/skills" -iname SKILL.md -not -path '*/node_modules/*' -print0 | sort -z)

[ "$found" = 1 ] || { echo "skills/ 下没有任何 SKILL.md"; exit 1; }
echo
echo "通过 $pass，失败 $fail，提醒 $warn"
[ "$fail" = 0 ]
