#!/usr/bin/env python3
"""填模板：把一件 DOCX 打成带编号的清单，再把模型写的差量原地施加回去。只依赖 python-docx，离线。

依据 ADR-0023「出件走填模板差量」，原语从 2026-09-14 的原型搬（六条结论在 docs/research/to-docx-差量原型.md）。
模型不重写整篇：读清单、只提交编号处的改动，骨架与表格几何由构造保住。

两个子命令：
  list   把正文打成清单：正文里全部 w:p 按文档顺序编 p0、p1…（单元格里的段落也在序列里，行前标表、行、格），
         一段里的槽按占位正则从左到右编 #1、#2…，清单里写成 ⟦1 XX年X月X日⟧；已高亮的区间写成 ⟪…⟫；
         「（注：…）」开头的段前标 [说明]。--plain 出同一份正文的纯文本（不带任何标记），指南整读用它。
  apply  施加差量，写出一件 DOCX。改动一律落到「段落里的字符区间」上，不落到 run 序号上：占位在官方模板里
         大多横跨 run。施加完后没被填也没高亮的槽由代码一律加黄，模型不必逐个写；元数据收尾无条件清掉。
         --out 可直接写 文书/ 下的路径并覆盖（重出覆盖同一份，载体与产物可以是同一路径）；不给就写临时位置。

差量的形状（一个 JSON 数组，一条一个改动）：

  [{"op":"fill","at":"p2#1","text":"某年某月某日"},
   {"op":"fill","at":"p2#8","text":"某某","highlight":true},
   {"op":"replace","at":"p2","old":"XX公司（债权人名称）","new":"某甲公司"},
   {"op":"delete","at":"p14"},
   {"op":"highlight","at":"p3","text":"没把握的那句"},
   {"op":"unhighlight","at":"p7"}]

  fill 只认槽号（p2#1），text 为空串按「没填」处理（槽留原占位、由收尾留黄，不删 run、不拒）；replace 按原文换，
  `old` 在那一段里须唯一，new 为空串就是把那一处删掉（条件块取舍）；delete 删整段，单元格里唯一的段、带 sectPr
  的段、正文最后一张表之后仅剩的末段这三种改成清空（删了会让表直接接 sectPr 或单元格空掉，Word 会报修复）；
  highlight / unhighlight 可写槽号、可写 text 指一段原文、都不写则整段。同一段里的改动按区间从后往前施加，
  偏移互不影响。

拒改的两种（退出码 1，一个字都不写，--out 指的已有文件原样不动）：差量本身不合法（槽号越界、原文不唯一、
两处改动区间重叠）；槽所在 run 含脚注引用、图片或域代码（切开或换字会把它们跟着复制或丢掉）。这是确定性规则的
第二类（被检查的一方是模型自己，ADR-0024）；文书合不合格是判断，归模型与律师的眼睛，这里不查。

用哪个解释器归 agent（ADR-0018）：约束的是后端版本而不是哪一个 python，装法与四条约束见 SKILL.md 的
「跑得动脚本的环境」。版本对不上照常出件，只在回显里报出来。

用法：
  python fill.py list <文书或模板.docx> [--plain] [--slot-pattern <正则>]...
  python fill.py apply <文书或模板.docx> --diff <差量.json|-> [--out <输出.docx>]
                       [--no-highlight-rest] [--json] [--slot-pattern <正则>]...

退出码：0 写出（apply 的 stdout 第一行「已写出 <路径>」，第二行「出件环境：…」，第三行「改动段：…」，
其后是逐条日志）；1 拒绝（差量不合法、拒改的 run、文件打不开；原因在 stderr）；2 用法错误。
"""
import argparse
import copy
import datetime as _dt
import importlib.metadata
import json
import os
import pathlib
import re
import secrets
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.text.run import Run

TEMP_DIRNAME = "to-docx"
BACKEND = "python-docx"
MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "requirements.txt"  # 随包分发的依赖清单
SLOT_L, SLOT_R = "⟦", "⟧"      # 清单里的槽
HL_L, HL_R = "⟪", "⟫"          # 清单里已高亮的区间

# 占位的形状。顺序即优先级（先匹配到的赢），所以长的写在前：不然「XX年X月X日」会被「XX」先吃掉一截。
# **形状可加**：律师自己的空白模板换一套占位习惯时，往这张表里加一行；只对一次调用临时加则用 --slot-pattern。
SLOT_SHAPES = (
    ("日期", r"X+年X+月X*日?"),
    ("案号年份", r"（20X{1,2}）"),
    ("年份", r"20XX"),
    ("方括号块", r"【[^】\n]*】"),        # 也收整段的条件块「【若有异议：…】」
    ("X 串", r"X{2,}"),
    ("叉串", r"×{2,}"),
    ("下划线串", r"＿{2,}|_{3,}"),
    ("量词前的单个 X", r"(?<![A-Za-z])X(?=[家元名人份次个件笔项户万亿])"),
)
NOTE = re.compile(r"^\s*（?注[：:]")
# run 里许出现的子元素。别的（脚注引用、图片、域代码）一出现就拒改那一处：切开 run 要深拷贝，拷贝会把
# 它们跟着复制，换字会把它们丢掉，两样都是悄悄改坏文书（原型第 2 条的条件）。
RUN_PLAIN_CHILDREN = frozenset(qn(t) for t in (
    "w:rPr", "w:t", "w:tab", "w:br", "w:cr", "w:noBreakHyphen", "w:softHyphen", "w:lastRenderedPageBreak"))
RUN_CHILD_NAMES = {
    qn("w:footnoteReference"): "脚注引用", qn("w:endnoteReference"): "尾注引用",
    qn("w:drawing"): "图片", qn("w:pict"): "图片", qn("w:object"): "嵌入对象",
    qn("w:fldChar"): "域代码", qn("w:instrText"): "域代码", qn("w:fldSimple"): "域代码",
}


class Rejected(Exception):
    """拒改：差量不合法，或槽所在 run 含脚注引用、图片、域代码。退出码 1，什么都不写。"""


def compile_slots(extra: Optional[List[str]] = None) -> "re.Pattern":
    """出厂形状加上这次临时加的几条（--slot-pattern，可重复）。临时的排在后面，不抢出厂形状的先手。"""
    shapes = [p for _, p in SLOT_SHAPES] + list(extra or [])
    try:
        return re.compile("|".join(shapes))
    except re.error as e:
        raise Rejected("占位正则编译不了：%s" % e)


PLACEHOLDER = compile_slots()


# ---------------------------------------------------------------- 段落、run、区间

def paragraphs(doc) -> list:
    """正文里全部段落按文档顺序（含单元格里的）。下标即编号。"""
    return list(doc.element.body.iter(qn("w:p")))


def _runs(p) -> List[Tuple[object, int, int]]:
    """段落里的 run 及各自的字符区间 [(r, start, end)]。文字用 python-docx 的 Run.text（tab 记 \\t、br 记 \\n）。"""
    out = []
    pos = 0
    for r in p.iter(qn("w:r")):
        t = Run(r, None).text
        out.append((r, pos, pos + len(t)))
        pos += len(t)
    return out


def text_of(p) -> str:
    return "".join(Run(r, None).text for r in p.iter(qn("w:r")))


def _is_hl(r) -> bool:
    rpr = r.find(qn("w:rPr"))
    if rpr is None:
        return False
    h = rpr.find(qn("w:highlight"))
    if h is not None and h.get(qn("w:val")) not in (None, "none"):
        return True
    shd = rpr.find(qn("w:shd"))
    return shd is not None and (shd.get(qn("w:fill")) or "").upper() == "FFFF00"


def _set_hl(r, on: bool) -> None:
    Run(r, None).font.highlight_color = WD_COLOR_INDEX.YELLOW if on else None


def highlight_ranges(p) -> List[Tuple[int, int]]:
    """连续的高亮 run 并成一个区间。"""
    out = []  # type: List[Tuple[int, int]]
    for r, s, e in _runs(p):
        if e == s or not _is_hl(r):
            continue
        if out and out[-1][1] == s:
            out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def slots(p, pattern: "re.Pattern" = PLACEHOLDER) -> List[Tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in pattern.finditer(text_of(p))]


def _blocker(r) -> Optional[str]:
    """这个 run 里有没有不许碰的子元素；有就回它的人话名字。"""
    for child in r:
        if child.tag not in RUN_PLAIN_CHILDREN:
            return RUN_CHILD_NAMES.get(child.tag, str(child.tag).rsplit("}", 1)[-1])
    return None


def _guard(p, start: int, end: int, where: str) -> None:
    """区间沾到的每个 run 都得是纯文字 run，否则整条差量拒掉（宁可不改，不悄悄改坏）。"""
    for r, s, e in _runs(p):
        if e <= start or s >= end:
            continue
        bad = _blocker(r)
        if bad is not None:
            raise Rejected("%s 的槽所在 run 含%s，拒改（切开或换字会把它复制或丢掉）" % (where, bad))


def _cut(p, k: int) -> None:
    """把落在字符 k 处的 run 切成两个，rPr 原样各留一份。k 正好在 run 边界上就不动。"""
    for r, s, e in _runs(p):
        if s < k < e:
            t = Run(r, None).text
            left = copy.deepcopy(r)
            r.addprevious(left)
            Run(left, None).text = t[:k - s]
            Run(r, None).text = t[k - s:]
            return


def replace_range(p, start: int, end: int, new_text: Optional[str], highlight: Optional[bool]) -> None:
    """段落字符区间 [start, end) 的改动原语：new_text 不为 None 就换成它（格式取区间里第一个 run 的）；
    highlight True/False 给区间加、去黄，None 不动。区间外的 run 一个不碰。"""
    _cut(p, end)
    _cut(p, start)
    covered = [r for r, s, e in _runs(p) if s >= start and e <= end and e > s]
    if not covered:
        raise Rejected("区间 [%d,%d) 没有覆盖任何 run" % (start, end))
    if new_text is not None:
        first = covered[0]
        Run(first, None).text = new_text
        for r in covered[1:]:
            r.getparent().remove(r)
        covered = [first]
        if new_text == "":
            first.getparent().remove(first)
            return
    if highlight is not None:
        for r in covered:
            _set_hl(r, highlight)


def _table_would_meet_sectpr(p) -> bool:
    """删了这一段，正文最后一张表会不会直接接上 sectPr：前一个兄弟是表、后面再没有段或表。
    Word 打开那样的件会报修复（2.0 推断的风险，ADR-0024 搬进施加构造）。"""
    if p.getparent().tag != qn("w:body"):
        return False
    prev = p.getprevious()
    if prev is None or prev.tag != qn("w:tbl"):
        return False
    return not any(el.tag in (qn("w:p"), qn("w:tbl")) for el in p.itersiblings())


def _delete_paragraph(p) -> str:
    """删整段。三种不能删、改成清空文字：单元格里最后一段（tc 至少要有一个 p）、带 sectPr 的段、正文最后一张表
    之后仅剩的末段（表直接接 sectPr）。"""
    ppr = p.find(qn("w:pPr"))
    parent = p.getparent()
    keep = (ppr is not None and ppr.find(qn("w:sectPr")) is not None) or \
           (parent.tag == qn("w:tc") and len(parent.findall(qn("w:p"))) == 1) or \
           _table_would_meet_sectpr(p)
    if keep:
        for r in list(p.iter(qn("w:r"))):
            r.getparent().remove(r)
        return "清空（不能整段删）"
    parent.remove(p)
    return "删段"


# ---------------------------------------------------------------- 打清单

def _where(p, doc) -> str:
    tcs = p.xpath("ancestor::w:tc[1]")
    if not tcs:
        return ""
    tc = tcs[0]
    tr = tc.getparent()
    tbl = tr.getparent()
    tables = list(doc.element.body.iter(qn("w:tbl")))
    return "[表%d 行%d 格%d] " % (tables.index(tbl) + 1, tbl.findall(qn("w:tr")).index(tr) + 1,
                                 tr.findall(qn("w:tc")).index(tc) + 1)


def _mark(text: str, sl: List[Tuple[int, int, str]], hl: List[Tuple[int, int]]) -> str:
    """把槽与高亮区间标进文字里：槽 ⟦n 原文⟧，高亮 ⟪…⟫。按字符位置插入。"""
    inserts = {}  # type: Dict[int, List[str]]
    for n, (s, e, _) in enumerate(sl, 1):
        inserts.setdefault(s, []).append(SLOT_L + str(n) + " ")
        inserts.setdefault(e, []).insert(0, SLOT_R)
    for s, e in hl:
        inserts.setdefault(s, []).insert(0, HL_L)
        inserts.setdefault(e, []).append(HL_R)
    out = []
    for i, ch in enumerate(text):
        out.extend(inserts.get(i, []))
        out.append(ch)
    out.extend(inserts.get(len(text), []))
    return "".join(out)


def listing(doc, pattern: "re.Pattern" = PLACEHOLDER) -> str:
    """模型读的那一份：一段一行，带编号、表格坐标、槽、已高亮区间与说明段标记。"""
    lines = []
    for i, p in enumerate(paragraphs(doc)):
        t = text_of(p)
        tag = "[说明] " if NOTE.match(t) else ""
        lines.append("p%d %s%s%s" % (i, _where(p, doc), tag, _mark(t, slots(p, pattern), highlight_ranges(p))))
    return "\n".join(lines) + "\n"


def plain_text(doc) -> str:
    """同一份正文，不带任何标记：整读一份指南或一份现成文书用这个。"""
    return "\n".join(text_of(p) for p in paragraphs(doc)) + "\n"


# ---------------------------------------------------------------- 施加差量

OPS = ("fill", "replace", "delete", "highlight", "unhighlight")


def _parse_at(at: str) -> Tuple[int, Optional[int]]:
    m = re.match(r"^p(\d+)(?:#(\d+))?$", at or "")
    if not m:
        raise Rejected("位置写法不对：%r（要 p3 或 p3#2）" % (at,))
    return int(m.group(1)), (int(m.group(2)) if m.group(2) else None)


def _planned(idx: int, p, plist: List[dict], pattern: "re.Pattern") -> Tuple[List[Tuple[int, int, Optional[str], Optional[bool], str]], List[str]]:
    """把一段里的几条改动算成字符区间；一处都不施加，只算与查。回 (要施加的区间, 按没填处理的那几条的日志)。"""
    text = text_of(p)
    sl = slots(p, pattern)
    planned = []
    skipped = []  # type: List[str]
    for op in plist:
        kind = op["op"]
        _, n = _parse_at(op["at"])
        hl = {"highlight": True, "unhighlight": False}.get(kind, op.get("highlight"))
        if n is not None:
            if kind == "replace":
                raise Rejected("replace 按原文换，位置只写段号：%s" % op["at"])
            if n < 1 or n > len(sl):
                raise Rejected("p%d 只有 %d 个槽，没有 #%d" % (idx, len(sl), n))
            s, e, old = sl[n - 1]
        elif kind == "fill":
            raise Rejected("fill 要写槽号（如 p%d#1）：%s" % (idx, op["at"]))
        elif kind == "replace" or (kind in ("highlight", "unhighlight") and "text" in op):
            old = op.get("old") if kind == "replace" else op.get("text")
            if not old:
                raise Rejected("p%d 的 %s 缺原文（replace 写 old，highlight 写 text）" % (idx, kind))
            if text.count(old) != 1:
                raise Rejected("p%d 里「%s」出现 %d 次，须唯一" % (idx, old, text.count(old)))
            s = text.index(old)
            e = s + len(old)
        else:
            s, e, old = 0, len(text), text
        if kind == "fill":
            new = op.get("text")
            if new is None:
                raise Rejected("p%d#%d 的 fill 缺 text" % (idx, n))
            if new == "":
                # 空串不是一个值：按「没填」处理，槽留原占位、由收尾留黄。不拒：拒改是内容检查，模型会学着删槽过检。
                skipped.append("fill %s「%s」空串：按没填处理，留黄" % (op["at"], old))
                continue
        elif kind == "replace":
            new = op.get("new")
            if new is None:
                raise Rejected("p%d 的 replace 缺 new" % idx)
        else:
            new = None
        if new == "" and hl:
            # 换成空串就是把那一处删掉，删掉的东西没法标黄。与其把 highlight 悄悄吞掉，不如拒掉整条差量。
            raise Rejected("p%d 的 %s 把那一处换成空串又要标黄：删掉的东西没有东西可标" % (idx, kind))
        planned.append((s, e, new, hl, "%s %s「%s」→「%s」" % (kind, op["at"], old, new if new is not None else "")))
    planned.sort(key=lambda x: x[0], reverse=True)
    for a in range(len(planned) - 1):
        if planned[a + 1][1] > planned[a][0]:
            raise Rejected("p%d 的两处改动区间重叠" % idx)
    return planned, skipped


def apply(doc, ops: List[dict], highlight_rest: bool = True,
          pattern: "re.Pattern" = PLACEHOLDER) -> Tuple[List[int], List[str], List[str]]:
    """施加差量，回 (改动过的段落号, 逐条日志, 留黄日志)。

    段落号按**施加之后**的文档重新算：删了段，后面的段号整体前移，模型抄进审查报告的是写出来那件里的段。
    按没填处理的 fill 不算改动，那一段没有别的改动就不进改动段。
    """
    ps = paragraphs(doc)
    by_para = {}   # type: Dict[int, List[dict]]
    deletes = []   # type: List[int]
    for op in ops:
        if not isinstance(op, dict):
            raise Rejected("差量的每一条都要是对象：%r" % (op,))
        kind = op.get("op")
        if kind not in OPS:
            raise Rejected("没有 %r 这种改动（只有 %s）" % (kind, "、".join(OPS)))
        idx, _ = _parse_at(op.get("at"))
        if idx >= len(ps):
            raise Rejected("没有 p%d（这件一共 %d 段）" % (idx, len(ps)))
        if kind == "delete":
            deletes.append(idx)
        else:
            by_para.setdefault(idx, []).append(op)
    # 先整篇算完、查完，再动第一处：拒改的件一个字都不改（fail-closed）
    plans = []
    for idx in sorted(by_para):
        planned, skipped = _planned(idx, ps[idx], by_para[idx], pattern)
        for s, e, _, _, _ in planned:
            _guard(ps[idx], s, e, "p%d" % idx)
        plans.append((idx, planned, skipped))

    log = []      # type: List[str]
    changed = []  # type: list
    for idx, planned, skipped in plans:
        p = ps[idx]
        log.extend(skipped)
        for s, e, new, hl, note in planned:
            replace_range(p, s, e, new, hl)
            log.append(note)
        if planned:
            changed.append(p)
    for idx in sorted(set(deletes), reverse=True):
        p = ps[idx]
        head = text_of(p)[:20]
        log.append("delete p%d：%s「%s」" % (idx, _delete_paragraph(p), head))

    rest = []  # type: List[str]
    if highlight_rest:
        for idx, p in enumerate(ps):
            if p.getparent() is None:
                continue
            hl = highlight_ranges(p)
            for s, e, old in reversed(slots(p, pattern)):
                if any(a <= s and e <= b for a, b in hl):
                    continue
                _guard(p, s, e, "p%d" % idx)
                replace_range(p, s, e, None, True)
                rest.append("留黄 p%d「%s」" % (idx, old))

    final = {}
    for i, p in enumerate(paragraphs(doc)):
        final[id(p)] = i
    return sorted(final[id(p)] for p in changed if id(p) in final), log, rest


# ---------------------------------------------------------------- 收尾：元数据

def clear_metadata(doc) -> None:
    """收尾无条件清元数据（2.0 的真实事故，落进确定性规则第一类：施加的构造，不是一条检查，ADR-0024）：
    作者与最后修改者置空、修订号置 1、删上次打印时间、创建与修改时间置为本次生成时间。"""
    cp = doc.core_properties
    now = _dt.datetime.now(_dt.timezone.utc)
    cp.author = ""
    cp.last_modified_by = ""
    cp.revision = 1
    lp = cp._element.find("{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastPrinted")
    if lp is not None:
        cp._element.remove(lp)  # python-docx 不接受 None，须直接删元素
    cp.created = now
    cp.modified = now


def default_out_path(src: pathlib.Path) -> pathlib.Path:
    base = pathlib.Path(tempfile.gettempdir()) / TEMP_DIRNAME
    base.mkdir(parents=True, exist_ok=True)
    while True:
        candidate = base / ("%s-%s.docx" % (src.stem, secrets.token_hex(4)))
        if not candidate.exists():
            return candidate


# ---------------------------------------------------------------- 出件环境（ADR-0018）

def pinned_version() -> Optional[str]:
    """清单里钉的后端版本；读不到就 None。只用标准库：本脚本的第三方 import 仍然只有 docx。"""
    try:
        text = MANIFEST.read_text(encoding="utf-8")
    except OSError:
        return None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        name, sep, value = line.partition("==")
        if sep and name.strip().lower().replace("_", "-") == BACKEND:
            return value.strip()
    return None


def runtime_version() -> Optional[str]:
    """这次真正跑起来的 python-docx 版本，问运行时要，不照抄清单。"""
    try:
        return importlib.metadata.version(BACKEND)
    except importlib.metadata.PackageNotFoundError:
        return None


def environment_line() -> str:
    """回显里那一行出件环境：恒常写，模型原样抄进审查报告的「生成依据」段（ADR-0018）。

    版本对不上照常出件、退出码照旧是 0，只在这一行里明写它不是钉住的那个版本：缺能力不阻断，但不把没量过
    的说成量过了。
    """
    actual = runtime_version()
    pinned = pinned_version()
    if actual is None:
        backend = "%s 版本查不出来（这个解释器上没有它的包元数据）" % BACKEND
    elif pinned is None:
        backend = "%s %s（依赖清单读不到，无从比对）" % (BACKEND, actual)
    elif actual == pinned:
        backend = "%s %s（与依赖清单钉的一致）" % (BACKEND, actual)
    else:
        backend = "%s %s（依赖清单钉的是 %s，这不是钉住的那个版本）" % (BACKEND, actual, pinned)
    return "出件环境：解释器 %s（python %d.%d.%d）；%s" % (
        sys.executable, sys.version_info[0], sys.version_info[1], sys.version_info[2], backend)


# ---------------------------------------------------------------- CLI

def open_docx(path: pathlib.Path):
    if not path.is_file():
        raise Rejected("打不开：%s 不在" % path)
    try:
        return docx.Document(str(path))
    except Exception as e:  # python-docx 对坏件抛的东西不止一种，一律当「打不开」
        raise Rejected("打不开：%s（%s：%s）" % (path, type(e).__name__, e))


def read_diff(spec: str) -> List[dict]:
    try:
        text = sys.stdin.read() if spec == "-" else pathlib.Path(spec).read_text(encoding="utf-8")
    except OSError as e:
        raise Rejected("差量读不到：%s（%s）" % (spec, e))
    except UnicodeDecodeError:
        raise Rejected("差量不是 UTF-8：%s" % spec)
    try:
        ops = json.loads(text)
    except ValueError as e:
        raise Rejected("差量不是合法 JSON：%s" % e)
    if not isinstance(ops, list):
        raise Rejected("差量要是一个数组，实际是 %s" % type(ops).__name__)
    return ops


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="fill.py", description="填模板：打带编号的清单，按差量原地施加。")
    sub = ap.add_subparsers(dest="cmd", required=True)

    lst = sub.add_parser("list", help="把正文打成带编号的清单")
    lst.add_argument("docx", help="要读的文书或空白模板（.docx）")
    lst.add_argument("--plain", action="store_true", help="出不带任何标记的纯文本（整读用）")
    lst.add_argument("--slot-pattern", action="append", default=[], help="临时多认一种占位形状（正则，可重复）")

    app = sub.add_parser("apply", help="按差量施加，写出一件新的 DOCX")
    app.add_argument("docx", help="载体：空白模板或这个节点当前的文书（.docx）；只有 --out 指到它时才被覆盖")
    app.add_argument("--diff", required=True, help="差量 JSON 的路径；写 - 从标准输入读")
    app.add_argument("--out", help="输出路径，可直接写 文书/ 下的路径，已存在就覆盖（重出覆盖同一份）；"
                                   "不给则写到 %%TEMP%%/to-docx/ 下并打印路径")
    app.add_argument("--no-highlight-rest", action="store_true",
                     help="不给剩下的槽自动加黄（默认自动加，模型不必逐个写）")
    app.add_argument("--json", action="store_true", help="结果按 JSON 打印")
    app.add_argument("--slot-pattern", action="append", default=[], help="临时多认一种占位形状（正则，可重复）")
    return ap


def cmd_list(args) -> int:
    doc = open_docx(pathlib.Path(args.docx))
    text = plain_text(doc) if args.plain else listing(doc, compile_slots(args.slot_pattern))
    sys.stdout.write(text)
    return 0


def cmd_apply(args) -> int:
    src = pathlib.Path(args.docx)
    doc = open_docx(src)
    ops = read_diff(args.diff)
    out = pathlib.Path(args.out) if args.out else default_out_path(src)
    # 先整篇施加完、清完元数据，再落盘：拒改在这一行之前抛出，--out 指的已有文件（含载体本身）一个字都不动。
    changed, log, rest = apply(doc, ops, not args.no_highlight_rest, compile_slots(args.slot_pattern))
    clear_metadata(doc)
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(out.name + ".part")
    doc.save(str(part))
    os.replace(str(part), str(out))   # 写完整件再换名：覆盖同一份时不会留下半成品
    if args.json:
        print(json.dumps({"产物": str(out), "出件环境": environment_line(), "改动段": changed,
                          "日志": log, "留黄": rest}, ensure_ascii=False, indent=2))
        return 0
    print("已写出 %s" % out)
    print(environment_line())
    print("改动段：%s" % (",".join(str(i) for i in changed) if changed else "无"))
    for line in log:
        print(line)
    print("代码留黄 %d 处" % len(rest))
    for line in rest:
        print(line)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return cmd_list(args) if args.cmd == "list" else cmd_apply(args)
    except Rejected as e:
        sys.stderr.write("拒绝：%s\n" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
