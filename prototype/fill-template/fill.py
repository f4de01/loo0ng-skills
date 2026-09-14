#!/usr/bin/env python3
"""原型（一次性代码，不进 main）：to-docx 的「填模板差量」路线在 python-docx 上走不走得通。

要验证的定义（ADR-0023 第四条）：代码把模板或当前文书的段落与单元格打成带编号清单，模型提交编号处的改动
（填、删段、加高亮、去高亮），代码在 docx 原地施加；门禁缩成两样：改动处没有残留占位且不在高亮里、几何不超阈值。

本文件是可以搬走的那一块（纯逻辑，不碰命令行）：
  listing(doc)                    -> 模型读的带编号清单（字符串）
  apply(doc, ops, highlight_rest) -> 原地施加差量，回 (改动了的段落号, 日志行)
  record_highlights(doc)          -> 审查报告里那份高亮清单（位置 + 原文 + 锚点）
  compare(doc, recorded)          -> 重出：比对上一次的高亮清单，律师填过的去黄
  check_changed(doc, changed)     -> 门禁第一样：改动处没有残留占位且不在高亮里
  geometry_snapshot(doc)          -> 表格几何与 run 格式的快照，前后比对用
python 3.9 + python-docx 1.2.0；不用 3.10 以上 API。

编号：正文里全部 w:p 按文档顺序编 p0、p1…（单元格里的段落也在内，清单里标出表/行/格）。
槽：一段里按占位正则从左到右编 #1、#2…；op 里 "p3#2" 指第 3 段第 2 个槽。
改动一律落到「段落里的字符区间」上：先把 run 在区间两端切开，再只动区间里的 run，区间外的 run 一个不碰。
高亮落成 w:highlight yellow（Word 里的荧光笔黄，律师用荧光笔工具能去掉）。
"""
import copy
import difflib
import json
import re
from typing import Dict, List, Optional, Tuple

from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.text.run import Run
from lxml import etree

# 占位的形状：从长到短，长的先匹配。X 也常单个出现在「X年X月X日」里，所以日期整体先匹配。
PLACEHOLDER = re.compile(
    r"X+年X+月X*日?|（20X{1,2}）|20XX|【[^】\n]*】|X{2,}|×{2,}|＿{2,}|_{3,}"
    r"|(?<![A-Za-z])X(?=[家元名人份次个件笔项户万亿])")   # 单个 X 带量词：X家、X元、X名
NOTE = re.compile(r"^\s*（?注[：:]")
SLOT_L, SLOT_R = "⟦", "⟧"      # 清单里的槽
HL_L, HL_R = "⟪", "⟫"          # 清单里已高亮的区间


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
    out: List[Tuple[int, int]] = []
    for r, s, e in _runs(p):
        if e == s or not _is_hl(r):
            continue
        if out and out[-1][1] == s:
            out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def slots(p) -> List[Tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in PLACEHOLDER.finditer(text_of(p))]


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
    highlight True/False 给区间加/去黄，None 不动。区间外的 run 一个不碰。"""
    _cut(p, end)
    _cut(p, start)
    covered = [r for r, s, e in _runs(p) if s >= start and e <= end and e > s]
    if not covered:
        raise ValueError("区间 [%d,%d) 没有覆盖任何 run" % (start, end))
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


def _delete_paragraph(p) -> str:
    """删整段。单元格里最后一段不能删（tc 至少一个 p），带 sectPr 的段不能删：这两种改成清空文字。"""
    ppr = p.find(qn("w:pPr"))
    parent = p.getparent()
    keep = (ppr is not None and ppr.find(qn("w:sectPr")) is not None) or \
           (parent.tag == qn("w:tc") and len(parent.findall(qn("w:p"))) == 1)
    if keep:
        for r in list(p.iter(qn("w:r"))):
            r.getparent().remove(r)
        return "清空（不能整段删）"
    parent.remove(p)
    return "删段"


# ---------------------------------------------------------------- 清单

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
    inserts: Dict[int, List[str]] = {}
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


def listing(doc) -> str:
    lines = []
    for i, p in enumerate(paragraphs(doc)):
        t = text_of(p)
        tag = "[说明] " if NOTE.match(t) else ""
        lines.append("p%d %s%s%s" % (i, _where(p, doc), tag, _mark(t, slots(p), highlight_ranges(p))))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 施加差量

def _parse_at(at: str) -> Tuple[int, Optional[int]]:
    m = re.fullmatch(r"p(\d+)(?:#(\d+))?", at)
    if not m:
        raise ValueError("位置写法不对：%s（要 p3 或 p3#2）" % at)
    return int(m.group(1)), (int(m.group(2)) if m.group(2) else None)


def apply(doc, ops: List[dict], highlight_rest: bool = True) -> Tuple[List[int], List[str]]:
    """施加差量。op 的形状：
      {"op":"fill","at":"p3#2","text":"某某公司"}                 填槽；加 "highlight":true 则填了仍标黄
      {"op":"replace","at":"p3","old":"（如有）","new":""}         按原文换（old 在段里须唯一），可加 "highlight"
      {"op":"delete","at":"p5"}                                    删整段
      {"op":"highlight","at":"p3#2"} / {"op":"highlight","at":"p3","text":"某句"} / {"op":"highlight","at":"p3"}
      {"op":"unhighlight", 同上}
    同一段里的改动按区间从后往前施加，前面的偏移不受影响；删段最后做。
    highlight_rest：施加完后，没被填、还没高亮的槽一律加黄（「缺的槽保留原占位加高亮」）。
    回 (改动过的段落号列表, 日志行)。"""
    ps = paragraphs(doc)
    by_para: Dict[int, List[dict]] = {}
    deletes: List[int] = []
    for op in ops:
        idx, _ = _parse_at(op["at"])
        if idx >= len(ps):
            raise ValueError("没有 p%d" % idx)
        if op["op"] == "delete":
            deletes.append(idx)
        else:
            by_para.setdefault(idx, []).append(op)
    log: List[str] = []
    changed: List[int] = []
    for idx, plist in by_para.items():
        p = ps[idx]
        text = text_of(p)
        sl = slots(p)
        planned = []  # (start, end, new_text, highlight, 说明)
        for op in plist:
            _, n = _parse_at(op["at"])
            kind = op["op"]
            hl = {"highlight": True, "unhighlight": False}.get(kind, op.get("highlight"))
            if n is not None:
                if n < 1 or n > len(sl):
                    raise ValueError("p%d 只有 %d 个槽，没有 #%d" % (idx, len(sl), n))
                s, e, old = sl[n - 1]
            elif kind == "replace" or (kind in ("highlight", "unhighlight") and "text" in op):
                old = op["old"] if kind == "replace" else op["text"]
                if text.count(old) != 1:
                    raise ValueError("p%d 里「%s」出现 %d 次，须唯一" % (idx, old, text.count(old)))
                s = text.index(old)
                e = s + len(old)
            else:
                s, e, old = 0, len(text), text
            new = op.get("text") if kind == "fill" else (op.get("new") if kind == "replace" else None)
            planned.append((s, e, new, hl, "%s %s「%s」→「%s」" % (kind, op["at"], old, new if new is not None else "")))
        planned.sort(key=lambda x: x[0], reverse=True)
        for a in range(len(planned) - 1):
            if planned[a + 1][1] > planned[a][0]:
                raise ValueError("p%d 的两处改动区间重叠" % idx)
        for s, e, new, hl, note in planned:
            replace_range(p, s, e, new, hl)
            log.append(note)
        changed.append(idx)
    for idx in sorted(set(deletes), reverse=True):
        log.append("delete p%d：%s「%s」" % (idx, _delete_paragraph(ps[idx]), text_of(ps[idx])[:20]))
        changed.append(idx)
    if highlight_rest:
        deleted = set(deletes)
        for idx, p in enumerate(ps):
            if idx in deleted or p.getparent() is None:
                continue
            hl = highlight_ranges(p)
            for s, e, old in reversed(slots(p)):
                if not any(a <= s and e <= b for a, b in hl):
                    replace_range(p, s, e, None, True)
                    log.append("留黄 p%d「%s」" % (idx, old))
    return sorted(set(changed)), log


# ---------------------------------------------------------------- 高亮清单与重出比对

def record_highlights(doc) -> List[dict]:
    """审查报告里的高亮清单：一处一行。段落号只是提示；键是「当时的整段文字」（重出时模糊匹配段落）加
    「高亮处原文」（判律师改没改）。不用字符偏移：律师增删段落、在段内填字都会让偏移飘。"""
    out = []
    for idx, p in enumerate(paragraphs(doc)):
        t = text_of(p)
        for k, (s, e) in enumerate(highlight_ranges(p)):
            out.append({"p": idx, "n": k, "para": t, "text": t[s:e]})
    return out


def _same_para(a: str, b: str) -> bool:
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def compare(doc, recorded: List[dict]) -> List[str]:
    """重出：对当前文书里每个带高亮的段落，先按整段文字模糊找上一次记的那一段；段里每处高亮，原文仍是记过的
    原文（多重集合里消一个）就仍待填、不动；不是则是律师填的，去黄。找不到记过的段落的高亮是律师自己加的，
    不动、只报。上次记了而这次没消掉的，是律师填了也去了黄（或整段删了）。"""
    lines = []
    consumed = set()
    for idx, p in enumerate(paragraphs(doc)):
        hl = highlight_ranges(p)
        if not hl:
            continue
        t = text_of(p)
        recs = [j for j, rec in enumerate(recorded) if _same_para(rec["para"], t)]
        for s, e in hl:
            cur = t[s:e]
            hit = next((j for j in recs if j not in consumed and recorded[j]["text"] == cur), None)
            if recs and hit is None:
                # 记过的段、没记过的原文：律师填了字没去黄
                replace_range(p, s, e, None, False)
                lines.append("p%d「%s」律师已填，去黄" % (idx, cur))
            elif hit is None:
                lines.append("p%d「%s」不在记过的段落里，律师自己加的黄，不动" % (idx, cur))
            else:
                consumed.add(hit)
                lines.append("p%d「%s」仍待填" % (idx, cur))
    for j, rec in enumerate(recorded):
        if j not in consumed:
            lines.append("原 p%d「%s」律师已填并去黄（或整段已删）" % (rec["p"], rec["text"]))
    return lines


# ---------------------------------------------------------------- 门禁第一样、几何快照

def check_changed(doc, changed: List[int]) -> List[str]:
    """改动处没有残留占位且不在高亮里。改动处以外不查（律师改过的位置不查）。"""
    fails = []
    ps = paragraphs(doc)
    for idx in changed:
        if idx >= len(ps):
            continue
        p = ps[idx]
        if p.getparent() is None:
            continue
        hl = highlight_ranges(p)
        for s, e, old in slots(p):
            if not any(a <= s and e <= b for a, b in hl):
                fails.append("p%d 残留占位「%s」且不在高亮里" % (idx, old))
    return fails


def _rpr_key(r) -> str:
    """run 格式去掉高亮后的样子，字符串化了好比对。"""
    rpr = r.find(qn("w:rPr"))
    if rpr is None:
        return ""
    rpr = copy.deepcopy(rpr)
    el = rpr.find(qn("w:highlight"))
    if el is not None:
        rpr.remove(el)
    return etree.tostring(rpr, encoding="unicode")


def geometry_snapshot(doc) -> Tuple[List[str], Dict[int, List[str]]]:
    """(表格几何：每张表的 tblPr/tblGrid/每行 trPr/每格 tcPr 的 XML, 每段的字符→格式串)。
    施加前后比：表格几何逐字节相同；改动段以外的段落，每个字符的格式相同。"""
    geo = []
    for tbl in doc.element.body.iter(qn("w:tbl")):
        for tag in ("w:tblPr", "w:tblGrid"):
            el = tbl.find(qn(tag))
            geo.append(etree.tostring(el, encoding="unicode") if el is not None else "")
        for tr in tbl.findall(qn("w:tr")):
            el = tr.find(qn("w:trPr"))
            geo.append(etree.tostring(el, encoding="unicode") if el is not None else "")
            for tc in tr.findall(qn("w:tc")):
                el = tc.find(qn("w:tcPr"))
                geo.append(etree.tostring(el, encoding="unicode") if el is not None else "")
    fmt: Dict[int, List[str]] = {}
    for idx, p in enumerate(paragraphs(doc)):
        chars = []
        for r, s, e in _runs(p):
            chars.extend([_rpr_key(r)] * (e - s))
        fmt[idx] = chars
    return geo, fmt


def dumps(recorded: List[dict]) -> str:
    return json.dumps(recorded, ensure_ascii=False, indent=1)
