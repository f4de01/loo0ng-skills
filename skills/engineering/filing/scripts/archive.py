#!/usr/bin/env python3
"""归档搬运 CLI：把收件箱里的文件按相对路径原样搬到去向格下。标准库零依赖，Windows 中文路径可用。

去向只有四格：材料、指南、模板/官方、模板/生成（ADR-0007）。判断去向归模型，本脚本只搬：
不改名、不覆盖、不越界、不合并目录；同名已存在则那件不搬、留在收件箱并报出；
压缩包与照片只能归材料（原样，不解压不识图）；永不写入 材料/律师陈述/。
不登记、不算指纹、不去重、不写图（图.json 一字不动）。

用法：
  python archive.py [--workspace <案件工作区>] list
  python archive.py [--workspace <案件工作区>] move --to <去向> <收件箱内相对路径>...

退出码：0 全部搬到；1 有拒绝（越界、不存在、去向不合规则时整条命令不搬；同名时那件不搬、其余照搬）；2 用法错误。
"""
import argparse
import os
import pathlib
import sys
from typing import List, NamedTuple, Optional, Tuple

WORKSPACE_MARKER = "图.json"
INBOX = "收件箱"
STATEMENTS_DIR = "律师陈述"  # 材料/律师陈述/ 归落档脚本，归档永不写入
DESTINATIONS = ("材料", "指南", "模板/官方", "模板/生成")
MATERIALS = "材料"
ARCHIVE_OR_PHOTO = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz",
                    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".webp"}


class Rejected(Exception):
    """整条命令拒绝：一件都不搬。"""


class Move(NamedTuple):
    rel: pathlib.PurePosixPath  # 收件箱内相对路径，回显用
    src: pathlib.Path
    target: pathlib.Path


def workspace_root(path: str) -> pathlib.Path:
    root = pathlib.Path(path).resolve()
    if not (root / WORKSPACE_MARKER).is_file():
        raise Rejected("%s 不是案件工作区（没有 %s）；请在案件目录里开会话" % (root, WORKSPACE_MARKER))
    return root


def inbox_relative(root: pathlib.Path, raw: str) -> pathlib.PurePosixPath:
    """把律师或模型给的相对路径规整成收件箱内的相对路径；绝对路径、.. 与越界都拒绝。"""
    text = raw.replace("\\", "/").strip()
    if not text:
        raise Rejected("路径为空")
    if pathlib.PureWindowsPath(text).is_absolute() or pathlib.PurePosixPath(text).is_absolute():
        raise Rejected("%s 是绝对路径；只收收件箱内的相对路径" % raw)
    rel = pathlib.PurePosixPath(text)
    if ".." in rel.parts:
        raise Rejected("%s 越界：路径里不得有 .." % raw)
    inbox = (root / INBOX).resolve()
    target = (inbox / rel).resolve()
    if inbox != target and inbox not in target.parents:
        raise Rejected("%s 越界：不在收件箱内" % raw)
    if target == inbox:
        raise Rejected("%s 指向收件箱本身" % raw)
    return rel


def first_archive_or_photo(path: pathlib.Path) -> Optional[pathlib.Path]:
    """文件按扩展名判；目录则找里面第一个压缩包或照片。没有返回 None。"""
    candidates = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for p in candidates:
        if p.suffix.lower() in ARCHIVE_OR_PHOTO:
            return p
    return None


def plan(root: pathlib.Path, dest: str, raws: List[str]) -> List[Move]:
    """先把每一件都验完再搬：任一件越界、不存在或去向不合规则，整条命令拒绝。"""
    inbox = root / INBOX
    moves = []
    seen = set()
    for raw in raws:
        rel = inbox_relative(root, raw)
        src = inbox / rel
        if not src.exists():
            raise Rejected("收件箱里没有 %s" % rel.as_posix())
        if dest == MATERIALS and rel.parts[0] == STATEMENTS_DIR:
            raise Rejected("%s 会落进 材料/%s/；那格只收落档脚本写的律师陈述，归档永不写入" % (rel.as_posix(), STATEMENTS_DIR))
        if dest != MATERIALS:
            hit = first_archive_or_photo(src)
            if hit is not None:
                raise Rejected("%s 是压缩包或照片，只能原样归 %s" % (hit.relative_to(inbox).as_posix(), MATERIALS))
        if rel in seen:
            raise Rejected("%s 给了两次" % rel.as_posix())
        seen.add(rel)
        moves.append(Move(rel, src, root / dest / rel))
    return moves


def prune_empty_dirs(inbox: pathlib.Path, start: pathlib.Path) -> None:
    """搬空的收件箱子目录顺手清掉，收件箱本身留着。"""
    cur = start
    while cur != inbox and cur.is_dir():
        try:
            cur.rmdir()
        except OSError:
            return
        cur = cur.parent


def move(root: pathlib.Path, dest: str, raws: List[str]) -> Tuple[List[str], List[str]]:
    moves = plan(root, dest, raws)
    done, refused = [], []
    inbox = root / INBOX
    for rel, src, target in moves:
        shown = "%s/%s" % (dest, rel.as_posix())
        if target.exists():
            refused.append("未搬：%s（%s 已存在，留在收件箱）" % (rel.as_posix(), shown))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # 同文件系统内改路径。不覆盖靠上面的存在检查；Windows 上 os.rename 遇已存在目标另会报错，POSIX 上不会。
        os.rename(src, target)
        prune_empty_dirs(inbox, src.parent)
        done.append("已归档：%s → %s" % (rel.as_posix(), shown))
    return done, refused


def list_inbox(root: pathlib.Path) -> List[str]:
    inbox = root / INBOX
    if not inbox.is_dir():
        return []
    return sorted(p.relative_to(inbox).as_posix() for p in inbox.rglob("*") if p.is_file())


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="archive.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=".", help="案件工作区（默认当前目录；开发侧测试用）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="列出收件箱里所有文件的相对路径")
    mv = sub.add_parser("move", help="把收件箱内的文件或目录原样搬到去向格下")
    mv.add_argument("--to", required=True, choices=DESTINATIONS, help="去向格")
    mv.add_argument("paths", nargs="+", metavar="收件箱内相对路径")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = workspace_root(args.workspace)
        if args.cmd == "list":
            names = list_inbox(root)
            print("\n".join(names) if names else "收件箱为空。")
            return 0
        done, refused = move(root, args.to, args.paths)
    except Rejected as e:
        print("拒绝：%s。一件都没搬。" % e, file=sys.stderr)
        return 1
    for line in done + refused:
        print(line)
    return 1 if refused else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
