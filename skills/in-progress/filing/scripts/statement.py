#!/usr/bin/env python3
"""陈述落档 CLI：把律师在对话里说的一句话落成 材料/律师陈述/ 下的一个文件。标准库零依赖，Windows 中文路径可用。

一条陈述一个文件，落盘后只读（ADR-0013）。文件名 YYYYMMDD-HHMMSS-<标题>.md；头部 front matter 六字段按行 键: 值，
顺序固定：性质、转述来源、录入时间、节点、回应、取代。正文：直接陈述与转述是 ## 原话（逐字）加可选 ## 整理（agent 整理的
项目 | 值 表）；裁定固定 ## 问题 ## 裁定 两段。取代关系只写在新文件里，旧文件一字不动。
脚本零语义：拟文件名、拒绝覆盖、校验转述必填来源、校验取代目标存在于同目录；标题里有没有人名、原话该不该整理归模型。

用法：
  python statement.py [--workspace <案件工作区>] --nature 直接陈述|转述|裁定 --title <标题> --words "<原话>"
                      [--source <转述来源>] [--node <节点标题>]... [--reply <审查报告相对路径>] [--supersedes <旧陈述文件名>]
                      [--item 项目=值]... [--question <问题>]

退出码：0 落盘；1 拒绝（原因在 stderr，什么都不写）；2 用法错误。
"""
import argparse
import datetime as _dt
import os
import pathlib
import stat
import sys
from typing import List, Optional

WORKSPACE_MARKER = "图.json"
STATEMENTS_DIR = pathlib.PurePosixPath("材料") / "律师陈述"
NATURES = ("直接陈述", "转述", "裁定")
NATURE_RELAY, NATURE_RULING = "转述", "裁定"
FIELDS = ("性质", "转述来源", "录入时间", "节点", "回应", "取代")
NODE_SEPARATOR = "；"
TITLE_MAX = 20


class Rejected(Exception):
    """落档拒绝：什么都不写。"""


def now() -> _dt.datetime:
    return _dt.datetime.now().astimezone()


def parse_at(text: Optional[str]) -> _dt.datetime:
    if not text:
        return now()
    try:
        t = _dt.datetime.fromisoformat(text)
    except ValueError:
        raise Rejected("--at 须是 ISO 8601 时刻，实际 %r" % text)
    return t if t.tzinfo else t.astimezone()


def workspace_root(path: str) -> pathlib.Path:
    root = pathlib.Path(path).resolve()
    if not (root / WORKSPACE_MARKER).is_file():
        raise Rejected("%s 不是案件工作区（没有 %s）；请在案件目录里开会话" % (root, WORKSPACE_MARKER))
    return root


def check_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise Rejected("标题为空")
    if len(title) > TITLE_MAX:
        raise Rejected("标题「%s」超过 %d 字" % (title, TITLE_MAX))
    bad = [c for c in title if not c.isalnum()]
    if bad:
        raise Rejected("标题「%s」含标点、空格或符号（%s）；只用汉字、字母、数字" % (title, "".join(bad)))
    return title


def single_line(value: Optional[str], label: str) -> str:
    value = (value or "").strip()
    if "\n" in value or "\r" in value:
        raise Rejected("%s 须是一行" % label)
    return value


def parse_items(items: List[str]) -> List[tuple]:
    rows = []
    for item in items:
        key, sep, value = item.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not key or not value:
            raise Rejected("--item 须写成 项目=值，实际 %r" % item)
        if "|" in key or "|" in value or "\n" in item:
            raise Rejected("--item 的项目与值不得含竖线或换行：%r" % item)
        rows.append((key, value))
    return rows


def check_supersedes(target_dir: pathlib.Path, name: str) -> str:
    name = single_line(name, "取代")
    if not name:
        return ""
    if name != pathlib.PurePath(name.replace("\\", "/")).name:
        raise Rejected("取代只写同目录里的文件名，不带路径：%r" % name)
    if not (target_dir / name).is_file():
        raise Rejected("取代目标 %s 不在 %s 里" % (name, STATEMENTS_DIR.as_posix()))
    return name


def render(front: List[tuple], body: str) -> str:
    head = ["---"] + ["%s: %s" % (k, v) if v else "%s:" % k for k, v in front] + ["---", ""]
    return "\n".join(head) + body.rstrip("\n") + "\n"


def compose_body(nature: str, words: str, items: List[tuple], question: str) -> str:
    if nature == NATURE_RULING:
        return "## 问题\n\n%s\n\n## 裁定\n\n%s\n" % (question, words)
    body = "## 原话\n\n%s\n" % words
    if items:
        table = ["| 项目 | 值 |", "| --- | --- |"] + ["| %s | %s |" % row for row in items]
        body += "\n## 整理\n\n以下由 agent 整理，不是律师原话；以上文原话为准。\n\n%s\n" % "\n".join(table)
    return body


def write_statement(args) -> str:
    root = workspace_root(args.workspace)
    target_dir = root / STATEMENTS_DIR
    at = parse_at(args.at)
    title = check_title(args.title)
    words = args.words.strip()
    if not words:
        raise Rejected("原话为空")
    source = single_line(args.source, "转述来源")
    if args.nature == NATURE_RELAY and not source:
        raise Rejected("性质为转述时转述来源必填（--source）")
    if args.nature != NATURE_RELAY and source:
        raise Rejected("只有转述才有转述来源；性质 %s 不带 --source" % args.nature)
    question = single_line(args.question, "问题") if args.question else ""
    if args.nature == NATURE_RULING and not question:
        raise Rejected("性质为裁定时须给 --question（问题）")
    if args.nature != NATURE_RULING and args.question is not None:
        raise Rejected("只有裁定才有问题段；性质 %s 不带 --question" % args.nature)
    items = parse_items(args.item or [])
    if args.nature == NATURE_RULING and items:
        raise Rejected("裁定正文固定为问题与裁定两段，不带 --item")
    nodes = [single_line(n, "节点") for n in (args.node or [])]
    if any(not n for n in nodes):
        raise Rejected("节点标题为空")
    reply = single_line(args.reply, "回应")
    supersedes = check_supersedes(target_dir, args.supersedes or "")

    filename = "%s-%s.md" % (at.strftime("%Y%m%d-%H%M%S"), title)
    path = target_dir / filename
    if path.exists():
        raise Rejected("%s/%s 已存在，拒绝覆盖；隔一秒再落或换标题" % (STATEMENTS_DIR.as_posix(), filename))

    front = [("性质", args.nature), ("转述来源", source), ("录入时间", at.isoformat(timespec="seconds")),
             ("节点", NODE_SEPARATOR.join(nodes)), ("回应", reply), ("取代", supersedes)]
    text = render(front, compose_body(args.nature, words, items, question))
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    shown = "%s/%s" % (STATEMENTS_DIR.as_posix(), filename)
    return "已落档：%s%s" % (shown, "（取代 %s）" % supersedes if supersedes else "")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="statement.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=".", help="案件工作区（默认当前目录；开发侧测试用）")
    ap.add_argument("--at", help="录入时刻（ISO 8601；默认此刻；开发侧测试用）")
    ap.add_argument("--nature", required=True, choices=NATURES, help="性质")
    ap.add_argument("--title", required=True, help="标题：不超 %d 字、不含人名、无标点，进文件名" % TITLE_MAX)
    ap.add_argument("--words", required=True, help="律师原话，逐字")
    ap.add_argument("--source", help="转述来源（仅转述，必填）")
    ap.add_argument("--node", action="append", help="关联节点的图内唯一标题，可重复")
    ap.add_argument("--reply", help="回应哪份审查报告（工作区内相对路径）")
    ap.add_argument("--supersedes", help="取代哪条旧陈述（同目录文件名）")
    ap.add_argument("--item", action="append", metavar="项目=值", help="一句话带多个值时的整理行，可重复")
    ap.add_argument("--question", help="裁定回答的问题（仅裁定，必填）")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        line = write_statement(args)
    except Rejected as e:
        print("拒绝：%s" % e, file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
