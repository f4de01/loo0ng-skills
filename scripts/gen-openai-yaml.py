#!/usr/bin/env python3
"""从每件 skill 的 SKILL.md frontmatter 机械生成 agents/openai.yaml（ADR-0009）。标准库零依赖。

源是 frontmatter 里的 metadata.display-name、metadata.short-description 与 disable-model-invocation；
产物只有 interface.display_name、interface.short_description，编排 skill 与路由（disable-model-invocation: true）
另加 policy.allow_implicit_invocation: false。写出的文件 LF、不带 BOM。
display-name 必须等于 skill 目录名（即 name）：Codex 的 $ 补全显示的是它，律师按 loo0ng- 名字找（#29，ADR-0009 附注）；
中文只进 short-description。

用法：
  python scripts/gen-openai-yaml.py [--check] [--skills skills]
递归扫 skills/<bucket>/<name>/SKILL.md（Matt 分桶布局，ADR-0009 附注 2026-09-13）。
退出码：0 全部同步（或已写出）；1 --check 下有不同步；2 frontmatter 缺字段或解析不了。
"""
import argparse
import pathlib
import sys
from typing import Dict, List, Tuple

DEFAULT_SKILLS = pathlib.Path("skills")
OUTPUT_REL = pathlib.Path("agents") / "openai.yaml"


class GenError(Exception):
    pass


def parse_frontmatter(text: str) -> Dict[str, object]:
    """读 --- 之间的 YAML 子集：顶层 键: 值，以及 metadata: 下两空格缩进的 键: 值；值可带引号。"""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        raise GenError("没有 frontmatter")
    data: Dict[str, object] = {}
    section = None
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, sep, value = line.strip().partition(":")
        if not sep:
            raise GenError("frontmatter 行解析不了：%r" % line)
        value = value.strip()
        if indent == 0:
            if value == "":
                section = key
                data[key] = {}
            else:
                section = None
                data[key] = unquote(value)
        elif section is not None:
            data[section][key] = unquote(value)  # type: ignore[index]
        else:
            raise GenError("frontmatter 缩进行没有归属：%r" % line)
    raise GenError("frontmatter 没有闭合的 ---")


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].replace('\\"', '"')
    return value


def render(front: Dict[str, object], skill_dir: pathlib.Path) -> str:
    meta = front.get("metadata")
    if not isinstance(meta, dict):
        raise GenError("%s 的 frontmatter 缺 metadata" % skill_dir.name)
    display = meta.get("display-name")
    short = meta.get("short-description")
    if not display or not short:
        raise GenError("%s 的 frontmatter 须有 metadata.display-name 与 metadata.short-description" % skill_dir.name)
    if display != skill_dir.name:
        raise GenError("%s 的 metadata.display-name 须等于目录名（Codex $ 补全显示它），实际 %r" % (skill_dir.name, display))
    out = ["interface:", '  display_name: "%s"' % display, '  short_description: "%s"' % short]
    if str(front.get("disable-model-invocation", "")).lower() == "true":
        out += ["policy:", "  allow_implicit_invocation: false"]
    return "\n".join(out) + "\n"


def skill_dirs(root: pathlib.Path) -> List[pathlib.Path]:
    """skills/<bucket>/<name>/SKILL.md，照 Matt 分桶递归找；桶下没有 SKILL.md 的目录（如只有 README.md 的空桶）不算。"""
    return sorted(p.parent for p in root.rglob("SKILL.md") if "node_modules" not in p.parts)


def generate(root: pathlib.Path, check: bool) -> Tuple[List[str], List[str]]:
    """返回 (改了或不同步的, 已同步的)。"""
    stale, fresh = [], []
    for d in skill_dirs(root):
        expected = render(parse_frontmatter((d / "SKILL.md").read_text(encoding="utf-8")), d)
        target = d / OUTPUT_REL
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current == expected:
            fresh.append(d.name)
            continue
        stale.append(d.name)
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(expected, encoding="utf-8", newline="\n")
    return stale, fresh


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gen-openai-yaml.py", description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="只比对不写，有不同步即退出码 1")
    ap.add_argument("--skills", default=str(DEFAULT_SKILLS), help="skills 根目录，默认 skills")
    args = ap.parse_args(argv)
    try:
        stale, fresh = generate(pathlib.Path(args.skills), args.check)
    except (GenError, OSError) as e:
        print("错误：%s" % e, file=sys.stderr)
        return 2
    for name in fresh:
        print("%s 已同步" % name)
    for name in stale:
        print("%s %s" % (name, "不同步" if args.check else "已生成 agents/openai.yaml"))
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
