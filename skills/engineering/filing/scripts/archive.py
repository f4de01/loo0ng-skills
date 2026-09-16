#!/usr/bin/env python3
"""归档 CLI：按模型写的归档计划把文件搬进本案，并维护归档索引。标准库零依赖，Windows 中文路径可用。

来源两种：`待归档/`（移动）与工作区外的任意目录（复制，原件不动）。去向只有三格：材料、参考/模板、
参考/指南（ADR-0023）。「去向」与「一句话是什么」是判断，归模型写进计划；本脚本只做确定性的那一半
（ADR-0024 第一类）：不改名、不覆盖、按内容哈希去重、子目录相对路径原样、外部来源只复制。
不解压、不识图、不做 OCR、不转 PDF；永不写 材料/律师说过的.md，永不写图。

用法：
  python archive.py [--workspace <案件工作区>] list [--from <工作区外目录>]
  python archive.py [--workspace <案件工作区>] apply --plan <计划.json> [--from <工作区外目录>] [--date YYYY-MM-DD]

计划是一个 JSON 数组，一条一件：路径、去向、说明三个必填字段，材料下可另给子目录（格式见 ARCHIVE-FORMAT.md）。

退出码：0 命令跑到底（逐件结果在回显里，含「已有」与「同名冲突」）；1 整条拒绝，一件不搬；2 用法错误。
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import shutil
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple

WORKSPACE_MARKER = "图.json"
PENDING = "待归档"
INDEX = "归档索引.md"
MATERIALS = "材料"
DESTINATIONS = ("材料", "参考/模板", "参考/指南")
SAYINGS = "材料/律师说过的.md"  # 律师说过的那份文件由出件追加，归档永不写它
TEXT_COLUMN = "原件"  # 「文本」列：本版全是原件；OCR 与 PDF 转文本是后续版本
PLAN_KEYS = ("路径", "去向", "说明", "子目录")
REQUIRED_KEYS = ("路径", "去向", "说明")
INDEX_COLUMNS = ("相对路径", "是什么", "归档日期", "文本")
INDEX_TABLE = ("| %s |" % " | ".join(INDEX_COLUMNS), "| --- | --- | --- | --- |")
INDEX_PREAMBLE = (
    "# 归档索引",
    "",
    "一行一件，由归档脚本追加与更新，按归档先后排列；出件开场先读它再决定读哪些原件。",
    "「文本」列现在全是「原件」：将来转出的文本放原件旁同名加 `.md`，这一列指向它。",
    "",
)


class Rejected(Exception):
    """整条命令拒绝：一件都不搬，索引一行不写。"""


class Item(NamedTuple):
    rel: str         # 来源目录内的相对路径，回显用
    src: pathlib.Path
    note: str        # 一句话是什么，进索引
    target_rel: str  # 工作区内相对路径（去向 + 子目录 + 来源子路径）
    target: pathlib.Path


class Outcome(NamedTuple):
    line: str                       # 回显一行
    row: Optional[Tuple[str, str]]  # 落进索引的 (相对路径, 一句话)；未搬的为 None
    kind: str                       # 已归档 / 已有 / 同名冲突


# ---------------------------------------------------------------- 路径与内容

def workspace_root(path: str) -> pathlib.Path:
    root = pathlib.Path(path).resolve()
    if not (root / WORKSPACE_MARKER).is_file():
        raise Rejected("%s 不是案件工作区（没有 %s）；请在案件目录里开会话" % (root, WORKSPACE_MARKER))
    return root


def source_root(root: pathlib.Path, raw: Optional[str]) -> Tuple[pathlib.Path, bool]:
    """回（来源目录, 是不是复制）。不给 --from 就是待归档（移动）；给了就得在工作区外（复制）。"""
    if raw is None:
        # 待归档/ 不在也不拒：出件开场无条件调 list，缺这一格答「没有文件」就到此为止。
        return root / PENDING, False
    src = pathlib.Path(raw).expanduser()
    if not src.is_dir():
        raise Rejected("--from %s 不是一个目录" % raw)
    src = src.resolve()
    if src == root or root in src.parents:
        raise Rejected("%s 在本案工作区里；工作区内只收 %s/（不传 --from），根上的文件先挪进 %s/"
                       % (raw, PENDING, PENDING))
    if src in root.parents:
        raise Rejected("%s 套着本案工作区；换一个不含工作区的目录" % raw)
    return src, True


def relative_in(base: pathlib.Path, raw: str, label: str) -> str:
    """把计划里的路径规整成来源目录内的相对路径；绝对路径、.. 与越界都拒绝。"""
    text = raw.replace("\\", "/").strip()
    if not text:
        raise Rejected("%s 的路径为空" % label)
    if pathlib.PureWindowsPath(text).is_absolute() or pathlib.PurePosixPath(text).is_absolute():
        raise Rejected("%s 是绝对路径；计划里只写来源目录内的相对路径" % raw)
    rel = pathlib.PurePosixPath(text)
    if ".." in rel.parts:
        raise Rejected("%s 越界：路径里不得有 .." % raw)
    target = (base / rel).resolve()
    if base != target and base not in target.parents:
        raise Rejected("%s 越界：不在 %s 里" % (raw, base))
    return rel.as_posix()


def subdir_of(raw: str, dest: str, label: str) -> str:
    """材料下的主题子目录；其余两格不收。"""
    text = raw.replace("\\", "/").strip().strip("/")
    if not text:
        return ""
    if dest != MATERIALS:
        raise Rejected("%s：只有 %s 下能建主题子目录，去向 %s 不收「子目录」" % (label, MATERIALS, dest))
    parts = pathlib.PurePosixPath(text).parts
    if pathlib.PureWindowsPath(text).is_absolute() or any(p in ("..", ".") for p in parts):
        raise Rejected("%s 的子目录 %s 不合法：只写 %s 下的相对路径，不得有 .. 或绝对路径" % (label, raw, MATERIALS))
    return "/".join(parts)


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files_under(base: pathlib.Path) -> List[str]:
    if not base.is_dir():
        return []
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())


def archived_index(root: pathlib.Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """扫三格里已归档的文件，回（内容哈希 → 相对路径, 文件名 → 相对路径）。多份同哈希或同名取排序第一份。

    每次现扫现算，不落哈希缓存：归档索引是律师读的一份清单，不是指纹表（CONTEXT.md「归档索引」）。
    """
    by_hash, by_name = {}, {}
    for dest in DESTINATIONS:
        base = root / dest
        for rel in files_under(base):
            shown = "%s/%s" % (dest, rel)
            by_hash.setdefault(digest(base / rel), shown)
            by_name.setdefault(pathlib.PurePosixPath(rel).name, shown)
    return by_hash, by_name


# ---------------------------------------------------------------- 计划

def load_plan(root: pathlib.Path, base: pathlib.Path, plan_path: str) -> List[Item]:
    """整份计划先验完再搬：任一条不合法，整条命令拒绝。"""
    try:
        raw = pathlib.Path(plan_path).read_text(encoding="utf-8")
    except OSError as e:
        raise Rejected("读不到计划 %s：%s" % (plan_path, e))
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise Rejected("计划 %s 不是合法 JSON：%s" % (plan_path, e))
    if not isinstance(data, list) or not data:
        raise Rejected("计划要是一个非空 JSON 数组，一条一件")

    items, seen_src, seen_target = [], set(), set()
    for i, entry in enumerate(data, 1):
        label = "第 %d 条" % i
        if not isinstance(entry, dict):
            raise Rejected("%s 不是一个对象" % label)
        extra = sorted(k for k in entry if k not in PLAN_KEYS)
        if extra:
            raise Rejected("%s 有不认得的字段：%s；只收 %s" % (label, "、".join(extra), "、".join(PLAN_KEYS)))
        for key in REQUIRED_KEYS:
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise Rejected("%s 缺 %s（三个字段都必填，写成一行文字）" % (label, key))
        sub_raw = entry.get("子目录", "")
        if not isinstance(sub_raw, str):
            raise Rejected("%s 的子目录要写成一行文字" % label)
        dest = entry["去向"].strip()
        if dest not in DESTINATIONS:
            raise Rejected("%s 的去向 %s 不是三格之一：%s" % (label, dest, "、".join(DESTINATIONS)))
        note = entry["说明"].strip()
        if "\n" in note or "\r" in note or "|" in note:
            raise Rejected("%s 的说明要是一行，且不得含竖线（它进索引表）" % label)
        sub = subdir_of(sub_raw, dest, label)

        rel = relative_in(base, entry["路径"], label)
        src = base / rel
        if not src.exists():
            raise Rejected("%s 里没有 %s" % (base, rel))
        if not src.is_file():
            raise Rejected("%s 是目录；索引一行一件，计划里逐个文件写（list 已经逐件列出来了）" % rel)
        if rel in seen_src:
            raise Rejected("%s 在计划里给了两次" % rel)
        seen_src.add(rel)

        target_rel = "/".join(x for x in (dest, sub, rel) if x)
        if target_rel == SAYINGS:
            raise Rejected("%s 会写到 %s；那份文件由出件追加，归档永不写它" % (rel, SAYINGS))
        if target_rel in seen_target:
            raise Rejected("计划里有两条都落到 %s" % target_rel)
        seen_target.add(target_rel)
        items.append(Item(rel, src, note, target_rel, root / target_rel))
    return items


# ---------------------------------------------------------------- 归档索引

def cells_of(line: str) -> List[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_block(lines: List[str]) -> Tuple[Optional[int], int]:
    """找索引自己那张表：回（表头行号, 表体之后的行号）。找不到表头回 (None, 0)。

    只认表头恰好是四列那一张，表体到第一条不以 | 开头的行为止。索引里别的表与手写的段落
    因此一字不动：认得出的只有这一张表里的行。
    """
    for n, line in enumerate(lines):
        if line.strip().startswith("|") and cells_of(line)[:4] == list(INDEX_COLUMNS):
            end = n + 1
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            return n, end
    return None, 0


def index_rows(lines: List[str], head: int, end: int) -> Dict[str, int]:
    """索引表里 相对路径 → 行号。分隔行与表头不算。"""
    rows = {}
    for n in range(head + 1, end):
        cells = cells_of(lines[n])
        if len(cells) < 4 or cells[0] in INDEX_COLUMNS or set(cells[0]) <= {"-", ":"}:
            continue
        rows.setdefault(cells[0], n)
    return rows


def write_index(root: pathlib.Path, rows: List[Tuple[str, str]], date: str) -> Tuple[int, int]:
    """新件插在表末，已有那一行原地更新；表外的行与已有行的顺序一字不动。回（新增, 更新）。"""
    if not rows:
        return 0, 0
    path = root / INDEX
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else list(INDEX_PREAMBLE)
    head, end = table_block(lines)
    if head is None:  # 索引不在、或在但没有这张表：把表头补到末尾
        if lines and lines[-1].strip():
            lines.append("")
        head, end = len(lines), len(lines) + len(INDEX_TABLE)
        lines.extend(INDEX_TABLE)
    where = index_rows(lines, head, end)
    added = updated = 0
    for target_rel, note in rows:
        line = "| %s | %s | %s | %s |" % (target_rel, note, date, TEXT_COLUMN)
        if target_rel in where:
            lines[where[target_rel]] = line
            updated += 1
        else:
            lines.insert(end, line)
            where[target_rel] = end
            end += 1
            added += 1
    with open(str(path), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return added, updated


# ---------------------------------------------------------------- 动作

def prune_empty_dirs(base: pathlib.Path, start: pathlib.Path) -> None:
    """搬空的待归档子目录顺手清掉，待归档本身留着。"""
    cur = start
    while cur != base and cur.is_dir():
        try:
            cur.rmdir()
        except OSError:
            return
        cur = cur.parent


def list_source(root: pathlib.Path, base: pathlib.Path) -> List[str]:
    """逐件列出来源目录，并给每件一个状态。

    「重名」是提示不是拦截：本案已归档的件里有同名不同内容的一件，去向还没定，拦不拦得看律师。
    `apply` 那一步的「同名冲突」是另一回事，它只在目标路径已经被占时才拦。
    """
    by_hash, by_name = archived_index(root)
    out, counts = [], {"新": 0, "已有": 0, "重名": 0}
    for rel in files_under(base):
        h = digest(base / rel)
        name = pathlib.PurePosixPath(rel).name
        if h in by_hash:
            counts["已有"] += 1
            out.append("%s\t已有 → %s" % (rel, by_hash[h]))
        elif name in by_name:
            counts["重名"] += 1
            out.append("%s\t重名 → %s（内容不同）" % (rel, by_name[name]))
        else:
            counts["新"] += 1
            out.append("%s\t新" % rel)
    if not out:
        return ["%s 里没有文件。" % base]
    out.append("共 %d 件：新 %d，已有 %d，重名 %d。" % (len(out), counts["新"], counts["已有"], counts["重名"]))
    return out


def apply_plan(root: pathlib.Path, base: pathlib.Path, copying: bool, items: List[Item], date: str) -> List[str]:
    by_hash, _ = archived_index(root)
    outcomes = []
    for item in items:
        h = digest(item.src)
        if h in by_hash:
            outcomes.append(Outcome("已有：%s（与 %s 内容相同，未搬）" % (item.rel, by_hash[h]), None, "已有"))
            continue
        if item.target.exists():
            outcomes.append(Outcome("同名冲突：%s → %s 已存在且内容不同，未搬，留在原处"
                                    % (item.rel, item.target_rel), None, "同名冲突"))
            continue
        item.target.parent.mkdir(parents=True, exist_ok=True)
        if copying:
            shutil.copy2(str(item.src), str(item.target))
        else:
            os.rename(str(item.src), str(item.target))
            prune_empty_dirs(base, item.src.parent)
        by_hash[h] = item.target_rel
        outcomes.append(Outcome("已归档：%s → %s%s"
                                % (item.rel, item.target_rel, "（复制，原件不动）" if copying else ""),
                                (item.target_rel, item.note), "已归档"))

    added, updated = write_index(root, [o.row for o in outcomes if o.row is not None], date)
    kinds = [o.kind for o in outcomes]
    lines = [o.line for o in outcomes]
    lines.append("共 %d 件：已归档 %d，已有 %d，同名冲突 %d；%s 新增 %d 行、更新 %d 行。"
                 % (len(outcomes), kinds.count("已归档"), kinds.count("已有"), kinds.count("同名冲突"),
                    INDEX, added, updated))
    return lines


def check_date(raw: Optional[str]) -> str:
    if not raw:
        return _dt.date.today().isoformat()
    try:
        return _dt.date.fromisoformat(raw).isoformat()
    except ValueError:
        raise Rejected("--date 须是 YYYY-MM-DD，实际 %r" % raw)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="archive.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=".", help="案件工作区（默认当前目录；开发侧测试用）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="逐件列出来源目录里的文件，并标出已有与重名")
    ls.add_argument("--from", dest="source", help="工作区外的来源目录（默认 %s/）" % PENDING)
    ap_apply = sub.add_parser("apply", help="按计划搬运并写索引")
    ap_apply.add_argument("--plan", required=True, help="归档计划 JSON（写在临时位置，不进工作区）")
    ap_apply.add_argument("--from", dest="source", help="工作区外的来源目录（默认 %s/，外部一律复制）" % PENDING)
    ap_apply.add_argument("--date", help="归档日期（YYYY-MM-DD，默认今天；开发侧测试用）")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = workspace_root(args.workspace)
        base, copying = source_root(root, args.source)
        if args.cmd == "list":
            lines = list_source(root, base)
        else:
            date = check_date(args.date)
            lines = apply_plan(root, base, copying, load_plan(root, base, args.plan), date)
    except Rejected as e:
        print("拒绝：%s。一件都没搬。" % e, file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
