#!/usr/bin/env python3
"""版式门禁：对一件 DOCX 做只读检查。门禁本体是零第三方依赖的计算层（静态检查加 CJK 版面推算），
真实渲染（Word COM 经 powershell.exe 子进程出 PDF，PyMuPDF 读）降为机会性加信。

依据 ADR-0017（取代 ADR-0006 里「无渲染后端即报错」那一条）。门禁本体只用标准库，不新增任何依赖；
PyMuPDF 是可选件，只在拿到渲染结果时才 import。缺 Word / WPS / 其他软件不阻断出件：渲染层失败即跳过，
只写一条披露项，三项几何判据改用推算区间给结论。

结论三档，整件取最重的一档（不通过 > 需人眼 > 通过）：
  推算器给出区间 [lo, hi]、阈值 T：T < lo 该项不通过；T >= hi 该项通过；lo <= T < hi 该项需人眼。
  需人眼只可能由页数、空白页、最大行高三项产生；其余七项静态判据读 XML 得点值，恒为二值。
  有渲染结果时点值取代区间，需人眼当场坍缩；点值落在推算区间外时结论以点值为准，另出披露项
  「推算区间不含实测值」，同时进审查报告与 stderr。

不通过项（客观几何与结构，任一命中即不通过）：
  行高超阈值、页数超阈值（长标记撑列）；空白页（只有页码的页也算）；表宽超页面；页脚 PAGE 域写死（有
  --template 时还查丢失）；表格直接接 sectPr；docProps 残留作者 / 最后修改者 / 上次打印时间；正文残留模板
  占位标记（XX、【】等），有 --template 时还查模板里括号说明段整段残留；模板有表而成品一张表都没有（同样
  要有 --template）。
披露项（写进审查报告，不判不通过）：空单元格坐标；页数；无渲染结果时的那一条；有渲染结果时另有请求字体
  不在嵌入字体里、正文有字没渲出来（无渲染时这两条整条消失，不报「无」）。

fail-closed：守的不是落盘这道门，是不把测出来的事故当合格件交出去。转换器写在临时位置，本脚本
--deliver <目标> 在通过与需人眼两档把它一次性拷进工作区，位置相同、文件名不加装饰；不通过不落盘；
目标已存在则拒绝、不覆盖。

用法：
  python gate.py <文书.docx> [--template <模板.docx>] [--deliver <目标.docx>] [--json]
                 [--max-pages N] [--max-row-height 磅] [--powershell <exe>] [--no-render]

退出码：0 通过（有 --deliver 则已落盘）；1 不通过（不落盘）；3 需人眼（有 --deliver 则已落盘）；
2 门禁跑不动：文书或模板打不开、推算层自身抛异常、用法错误、落盘被拒。
"""
import argparse
import base64
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from typing import Dict, List, Optional, Tuple

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DEFAULT_PAGE_WIDTH = 11906  # A4，twips；sectPr 缺 pgSz/pgMar 时的兜底
DEFAULT_PAGE_HEIGHT = 16838
DEFAULT_MARGIN = 1440
DEFAULT_MAX_PAGES = 30
DEFAULT_MAX_ROW_HEIGHT = 200.0  # 磅；1-2 模板的印模行 116 磅，实测事故 250～313 磅
FOOTER_ZONE = 72.0  # 磅；页脚坐在下页边距里，底边 1 英寸内的字当页脚
PAGE_NUMBER_ONLY = re.compile(r"^[\s\d\-–/第页共]*$")
PLACEHOLDER = re.compile(r"X{2,}|×{2,}|＿{2,}|_{3,}|【[^】\n]{0,40}】")
NOTE_PARAGRAPH = re.compile(r"^（.{6,}）$")
TEMP_DIRNAME = "loo0ng-to-docx-gate"
CJK = re.compile(r"[㐀-鿿豈-﫿]")
# 中文字体名与 PDF 里 BaseFont 名的对应，只为披露项做归一，不求全
FONT_ALIASES = {
    "仿宋": "fangsong", "仿宋_gb2312": "fangsonggb2312", "宋体": "simsun", "黑体": "simhei", "楷体": "kaiti",
    "楷体_gb2312": "kaitigb2312", "微软雅黑": "microsoftyahei", "方正小标宋简体": "fzxiaobiaosong",
    "方正小标宋_gbk": "fzxiaobiaosong", "华文仿宋": "stfangsong", "华文中宋": "stzhongsong",
}
FONT_FALLBACK_NAMES = ("microsoftyahei",)  # Word 用它替代缺失的方正字体，披露时点名

# 打开后先 ComputeStatistics(2)（页数）逼 Word 完成分页再导出：不这样做，带页脚 PAGE 域的多页文书导出后 Word 会
# 崩掉（RPC_E_DISCONNECTED），本机对 3-1、4-2 两件模板稳定复现（#28）。
PS_RENDER = r"""
$ErrorActionPreference = 'Stop'
try { $w = New-Object -ComObject Word.Application } catch { Write-Output ('NOWORD ' + $_.Exception.Message); exit 3 }
$w.Visible = $false
$w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open('{IN}', $false, $true, $false)
  $null = $d.ComputeStatistics(2)
  $d.ExportAsFixedFormat('{OUT}', 17)
  $d.Close(0)
  Write-Output 'OK'
} catch { Write-Output ('EXPORTFAIL ' + $_.Exception.Message); exit 4 }
finally { $w.Quit() }
"""


class CannotRun(Exception):
    """门禁跑不动：文书或模板打不开、推算层自身抛异常、用法错误。退出码 2，不是不通过。"""


class Refused(Exception):
    """落盘被拒（目标已存在等）：退出码 2，它不是「文书不合格」（ADR-0017）。"""


class NoRender(Exception):
    """拿不到渲染结果：不是错误。渲染层跳过、只写一条披露项，三项几何判据用推算区间（ADR-0017）。"""


# ---------------------------------------------------------------- 静态检查（zip + XML）

def _text(el) -> str:
    return "".join(t.text or "" for t in el.iter(W + "t"))


class Docx:
    """只读打开一件 DOCX，取正文、页脚、元数据、样式与页面尺寸。"""

    def __init__(self, path: pathlib.Path):
        self.path = path
        try:
            self.zip = zipfile.ZipFile(str(path))
            self.document = ET.fromstring(self.zip.read("word/document.xml"))
        except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
            raise CannotRun("不是能打开的 DOCX：%s（%s）" % (path, e))
        self.body = self.document.find(W + "body")
        if self.body is None:
            raise CannotRun("DOCX 没有 body：%s" % path)
        self.sect_pr = self.body.find(W + "sectPr")

    def blocks(self) -> List[ET.Element]:
        return [c for c in self.body if c.tag in (W + "p", W + "tbl")]

    def paragraph_texts(self) -> List[str]:
        return [_text(p) for p in self.body.findall(W + "p")]

    def tables(self) -> List[ET.Element]:
        return self.body.findall(W + "tbl")

    def body_text(self) -> str:
        return "\n".join(_text(b) for b in self.blocks())

    def text_chunks(self) -> List[str]:
        """正文的每个段落与每个单元格的文字（去空白），供与 PDF 渲出的字比对。"""
        chunks = []
        for p in self.body.iter(W + "p"):
            t = re.sub(r"\s+", "", _text(p))
            if t:
                chunks.append(t)
        return chunks

    def styles_root(self) -> Optional[ET.Element]:
        try:
            return ET.fromstring(self.zip.read("word/styles.xml"))
        except (KeyError, ET.ParseError):
            return None

    def _sect_int(self, tag: str, attr: str, fallback: int) -> int:
        el = self.sect_pr.find(W + tag) if self.sect_pr is not None else None
        value = el.get(W + attr) if el is not None else None
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def page_metrics(self) -> Tuple[int, int, int]:
        return (self._sect_int("pgSz", "w", DEFAULT_PAGE_WIDTH),
                self._sect_int("pgMar", "left", DEFAULT_MARGIN),
                self._sect_int("pgMar", "right", DEFAULT_MARGIN))

    def section_metrics(self) -> Tuple[int, int]:
        """版心的宽与高（twips）：推算层按它分页。"""
        width, left, right = self.page_metrics()
        height = self._sect_int("pgSz", "h", DEFAULT_PAGE_HEIGHT)
        top = self._sect_int("pgMar", "top", DEFAULT_MARGIN)
        bottom = self._sect_int("pgMar", "bottom", DEFAULT_MARGIN)
        return width - left - right, height - top - bottom

    def core(self) -> Dict[str, Optional[str]]:
        try:
            core = ET.fromstring(self.zip.read("docProps/core.xml"))
        except (KeyError, ET.ParseError):
            return {}
        out = {}
        for key, tag in (("作者", DC + "creator"), ("最后修改者", CP + "lastModifiedBy"), ("上次打印时间", CP + "lastPrinted")):
            el = core.find(tag)
            out[key] = None if el is None else (el.text or "")
        return out

    def footers(self) -> List[str]:
        """sectPr 引用的页脚部件的 XML 原文。"""
        if self.sect_pr is None:
            return []
        try:
            rels = ET.fromstring(self.zip.read("word/_rels/document.xml.rels"))
        except (KeyError, ET.ParseError):
            return []
        targets = {rel.get("Id"): rel.get("Target") for rel in rels.findall(REL + "Relationship")}
        out = []
        for ref in self.sect_pr.findall(W + "footerReference"):
            target = targets.get(ref.get(R + "id"))
            if not target:
                continue
            name = "word/" + target if not target.startswith("/") else target[1:]
            try:
                out.append(self.zip.read(name).decode("utf-8", "replace"))
            except KeyError:
                continue
        return out

    def requested_fonts(self) -> List[str]:
        """有字的 run 请求的字体：含中文的看 eastAsia，否则看 ascii。"""
        fonts = set()
        for r in self.body.iter(W + "r"):
            text = _text(r)
            if not text.strip():
                continue
            rpr = r.find(W + "rPr")
            rf = rpr.find(W + "rFonts") if rpr is not None else None
            if rf is None:
                continue
            attr = "eastAsia" if CJK.search(text) else "ascii"
            name = rf.get(W + attr) or rf.get(W + "eastAsia") or rf.get(W + "ascii")
            if name:
                fonts.add(name)
        return sorted(fonts)


def _footer_has_page_field(xml: str) -> bool:
    return bool(re.search(r"<w:instrText[^>]*>[^<]*\bPAGE\b", xml)) or bool(re.search(r'w:instr="[^"]*\bPAGE\b', xml))


def _footer_visible_text(xml: str) -> str:
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


def static_checks(doc: Docx, template: Optional[Docx]) -> Tuple[List[str], List[str]]:
    """七项静态判据：读 XML 得点值，没有区间，恒为二值，永远不产生需人眼（ADR-0017）。"""
    fails: List[str] = []
    notes: List[str] = []

    core = doc.core()
    leftovers = [k for k, v in core.items() if v is not None and (k == "上次打印时间" or v.strip())]
    if leftovers:
        fails.append("元数据残留：%s" % "、".join(leftovers))

    blocks = doc.blocks()
    if blocks and blocks[-1].tag == W + "tbl":
        fails.append("表格直接接 sectPr：正文最后一个块是表格，之后没有空段")

    width, left, right = doc.page_metrics()
    for i, tbl in enumerate(doc.tables(), 1):
        tblpr = tbl.find(W + "tblPr")
        ind = tblpr.find(W + "tblInd") if tblpr is not None else None
        ind_w = int(ind.get(W + "w")) if ind is not None and ind.get(W + "w") and (ind.get(W + "type") or "dxa") == "dxa" else 0
        grid = tbl.find(W + "tblGrid")
        cols = [int(g.get(W + "w")) for g in grid.findall(W + "gridCol")] if grid is not None else []
        table_w = sum(c for c in cols if c)
        tblw = tblpr.find(W + "tblW") if tblpr is not None else None
        if tblw is not None and (tblw.get(W + "type") or "") == "dxa" and tblw.get(W + "w"):
            table_w = max(table_w, int(tblw.get(W + "w")))
        if left + ind_w + table_w > width:
            fails.append("表宽超页面：第 %d 张表右边到 %d twips，纸边在 %d" % (i, left + ind_w + table_w, width))

    for i, tbl in enumerate(doc.tables(), 1):
        empties = []
        for r, tr in enumerate(tbl.findall(W + "tr"), 1):
            for c, tc in enumerate(tr.findall(W + "tc"), 1):
                if _is_vmerge_continuation(tc):
                    continue  # 纵向合并的续格本来就没字
                if not _text(tc).strip():
                    empties.append("第 %d 行第 %d 格" % (r, c))
        if empties:
            notes.append("空单元格：第 %d 张表 %s" % (i, "、".join(empties)))

    body_text = doc.body_text()
    hits = sorted(set(m.group(0) for m in PLACEHOLDER.finditer(body_text)))
    if hits:
        fails.append("模板占位残留：%s" % "、".join(h[:20] for h in hits[:8]))
    if template is not None:
        compact = re.sub(r"\s+", "", body_text)
        leftover_notes = []
        for t in template.paragraph_texts():
            t = t.strip()
            if NOTE_PARAGRAPH.match(t) and re.sub(r"\s+", "", t) in compact:
                leftover_notes.append(t[:20])
        if leftover_notes:
            fails.append("模板原文残留：%s" % "、".join(leftover_notes))
        if template.tables() and not doc.tables():
            fails.append("模板表缺失：模板有 %d 张表，成品一张都没有" % len(template.tables()))

    footers = doc.footers()
    has_field = any(_footer_has_page_field(f) for f in footers)
    if not has_field:
        digits = [f for f in footers if re.search(r"\d", _footer_visible_text(f))]
        if digits:
            fails.append("页脚 PAGE 域写死：页脚里有数字却没有 PAGE 域")
        elif template is not None and any(_footer_has_page_field(f) for f in template.footers()):
            fails.append("页脚 PAGE 域丢失：模板页脚有 PAGE 域，成品没有")
    return fails, notes


# ---------------------------------------------------------------- 版面推算（标准库，门禁本体）

# 官方模板里页面几何、列宽、字号全是死数，而 CJK 全角字符的 advance 恰好等于字号（w:sz 是半磅，故
# advance = sz/2 磅 = sz×10 twips）。于是「一格几行」是算术，不需要字体度量、不打开任何字体文件，
# 四种环境上给出同一个数（#55）。出的是区间不是点值：两组参数各跑一遍取上下界。
ESTIMATE_BOUNDS = {  # (西文相对字号的宽度, 单倍行距相对字号的倍数, 折行段落是否多算一行)
    "lo": (0.5, 1.15, False),
    "hi": (1.0, 1.35, True),
}
# 下面两条容差放宽的是**推算区间的宽度**，不是阈值：判定式那一侧一点缓冲都不加（ADR-0017「不加缓冲带」）。
# 行高的量测容差（沿用原型 prototype/版面推算 的常数）：PyMuPDF 的 row.bbox 含横线本身，渲染还有取整，
# 实测稳定比推算高约 1 磅。
ROW_HEIGHT_TOLERANCE = (0.98, 1.02, 2.0)
# 页数下界的余量。长文书的回归件实测（150 段 23 页、160 段 24 页，Word 与 WPS 同数）正好压在下界那一行数上，
# 一格余量都没有；而 lineRule=auto 的行高由真实字体的 ascent / descent 决定，律师那台机器的替换字体与开发机
# 不是同一套（ADR-0017 后果段留着的两条雾之一），行高小一点整篇就少一页。下界因此按比例放宽，上界本来就松。
# 余量按比例给（误差随篇幅累积），四舍五入到整页：短件不因此变宽，23 页让一页、30 页让两页。
PAGE_LOW_MARGIN = 0.05
DEFAULT_SZ = 21
DEFAULT_CELL_MAR = 108
CJK_WIDE = re.compile("[　-〿㐀-䶿一-鿿豈-﫿＀-￯]")


def _tw2pt(v: float) -> float:
    return v / 20.0


def _sz_of(rpr, fallback):
    if rpr is None:
        return fallback
    el = rpr.find(W + "sz")
    if el is None:
        el = rpr.find(W + "szCs")
    if el is None:
        return fallback
    try:
        return int(el.get(W + "val"))
    except (TypeError, ValueError):
        return fallback


def _spacing_of(ppr) -> Dict[str, object]:
    out = {}
    if ppr is None:
        return out
    sp = ppr.find(W + "spacing")
    if sp is not None:
        for k in ("before", "after", "line"):
            v = sp.get(W + k)
            if v is not None:
                try:
                    out[k] = int(v)
                except ValueError:
                    pass
        rule = sp.get(W + "lineRule")
        if rule:
            out["lineRule"] = rule
    return out


def _ind_of(ppr) -> Dict[str, float]:
    out = {"left": 0, "right": 0, "firstLine": 0}
    if ppr is None:
        return out
    ind = ppr.find(W + "ind")
    if ind is None:
        return out
    pairs = (("left", ("left", "start")), ("right", ("right", "end")), ("firstLine", ("firstLine",)))
    for key, attrs in pairs:
        for a in attrs:
            v = ind.get(W + a)
            if v is not None:
                try:
                    out[key] = int(v)
                except ValueError:
                    pass
                break
    fc = ind.get(W + "firstLineChars")
    if fc is not None:
        try:
            out["firstLineChars"] = int(fc)
        except ValueError:
            pass
    return out


class Styles:
    """styles.xml 的 sz / spacing 解析，带 basedOn 链与默认段落样式。"""

    def __init__(self, root):
        self.by_id = {}
        self.default_p = None
        self.doc_sz = DEFAULT_SZ
        self.doc_spacing = {}
        if root is None:
            return
        dd = root.find(W + "docDefaults")
        if dd is not None:
            rpr = dd.find(W + "rPrDefault/" + W + "rPr")
            if rpr is not None:
                self.doc_sz = _sz_of(rpr, self.doc_sz)
            ppr = dd.find(W + "pPrDefault/" + W + "pPr")
            if ppr is not None:
                self.doc_spacing = _spacing_of(ppr)
        for st in root.findall(W + "style"):
            sid = st.get(W + "styleId")
            if sid is None:
                continue
            self.by_id[sid] = st
            if st.get(W + "type") == "paragraph" and st.get(W + "default") == "1":
                self.default_p = sid

    def _chain(self, sid):
        seen, out = set(), []
        while sid and sid in self.by_id and sid not in seen:
            seen.add(sid)
            st = self.by_id[sid]
            out.append(st)
            b = st.find(W + "basedOn")
            sid = b.get(W + "val") if b is not None else None
        return out

    def resolve(self, style_id):
        sz, sp = self.doc_sz, dict(self.doc_spacing)
        chain = self._chain(style_id) if style_id else []
        if self.default_p and style_id != self.default_p:
            chain = chain + self._chain(self.default_p)
        for st in reversed(chain):
            rpr = st.find(W + "rPr")
            if rpr is not None:
                sz = _sz_of(rpr, sz)
            ppr = st.find(W + "pPr")
            if ppr is not None:
                sp.update(_spacing_of(ppr))
        return sz, sp


def _has_page_break(p) -> bool:
    for br in p.iter(W + "br"):
        if br.get(W + "type") == "page":
            return True
    return False


def _style_id(p):
    ppr = p.find(W + "pPr")
    if ppr is None:
        return None
    ps = ppr.find(W + "pStyle")
    return ps.get(W + "val") if ps is not None else None


def _run_sz(p, style_sz):
    ppr = p.find(W + "pPr")
    if ppr is not None:
        v = _sz_of(ppr.find(W + "rPr"), None)
        if v:
            return v
    for r in p.findall(W + "r"):
        v = _sz_of(r.find(W + "rPr"), None)
        if v:
            return v
    return style_sz


def _text_width_tw(text: str, font_tw: float, latin_ratio: float) -> float:
    """一段文字的总宽（twips）。CJK 全角 = 字号；西文按 latin_ratio 折算。"""
    w = 0.0
    for ch in text:
        if ch == "\t":
            w += font_tw * 2
        elif CJK_WIDE.match(ch):
            w += font_tw
        else:
            w += font_tw * latin_ratio
    return w


def _para_layout(p, styles: Styles, avail_tw: float, params) -> Tuple[int, float, float, float, bool]:
    """一个段落的排版量：(行数, 行高磅, 段前磅, 段后磅, 有没有字)。

    分开回行数与行高，是因为分页要按行切：Word 把放不下的段落拆在行边界上，整段挪到下一页会每段浪费一次，
    长文书上系统性多算页数（150 段的回归件实测 23 页，整段挪法推算下界 25 页，真值落在区间外）。
    """
    latin_ratio, line_factor, kinsoku = params
    style_sz, sp = styles.resolve(_style_id(p))
    sz = _run_sz(p, style_sz)
    font_pt = sz / 2.0
    font_tw = sz * 10.0  # 半磅 → twips：sz/2 磅 × 20
    ppr = p.find(W + "pPr")
    sp = dict(sp)
    sp.update(_spacing_of(ppr))
    ind = _ind_of(ppr)
    first_extra = ind.get("firstLine", 0)
    if "firstLineChars" in ind:
        first_extra = max(first_extra, ind["firstLineChars"] / 100.0 * font_tw)
    width = max(avail_tw - ind["left"] - ind["right"], font_tw)
    text = _text(p)
    if not text:
        lines, wrapped = 1, False
    else:
        total = _text_width_tw(text, font_tw, latin_ratio)
        first_w = max(width - first_extra, font_tw)
        if total <= first_w:
            lines, wrapped = 1, False
        else:
            lines = 1 + int((total - first_w + width - 1e-9) // width)
            wrapped = True
            if kinsoku:
                lines += 1
    rule = sp.get("lineRule", "auto")
    if rule in ("exact", "atLeast"):
        lh = _tw2pt(sp.get("line", int(font_pt * line_factor * 20)))
        if rule == "atLeast":
            lh = max(lh, font_pt * line_factor)
    else:
        lh = (sp.get("line", 240) / 240.0) * font_pt * line_factor
    return lines, lh, _tw2pt(sp.get("before", 0)), _tw2pt(sp.get("after", 0)), bool(text.strip())


def _para_height_pt(p, styles: Styles, avail_tw: float, params) -> Tuple[float, bool]:
    """一个段落整段的 (高磅, 有没有字)。单元格里的段落不跨页，用这个。"""
    lines, lh, before, after, has_text = _para_layout(p, styles, avail_tw, params)
    return lines * lh + before + after, has_text


def _grid_widths(tbl) -> List[int]:
    g = tbl.find(W + "tblGrid")
    out = []
    if g is None:
        return out
    for c in g.findall(W + "gridCol"):
        try:
            out.append(int(c.get(W + "w")))
        except (TypeError, ValueError):
            out.append(0)
    return out


def _cell_margins(tbl) -> Tuple[int, int, int, int]:
    left = right = DEFAULT_CELL_MAR
    top = bottom = 0
    pr = tbl.find(W + "tblPr")
    cm = pr.find(W + "tblCellMar") if pr is not None else None
    if cm is not None:
        pairs = (("left", "left"), ("start", "left"), ("right", "right"),
                 ("end", "right"), ("top", "top"), ("bottom", "bottom"))
        for tag, name in pairs:
            el = cm.find(W + tag)
            if el is None:
                continue
            try:
                v = int(el.get(W + "w"))
            except (TypeError, ValueError):
                continue
            if name == "left":
                left = v
            elif name == "right":
                right = v
            elif name == "top":
                top = v
            else:
                bottom = v
    return left, right, top, bottom


def _is_vmerge_continuation(tc) -> bool:
    """纵向合并的续格：<w:vMerge/> 不带 val（带 val="restart" 的是起始格）。"""
    tcpr = tc.find(W + "tcPr")
    if tcpr is None:
        return False
    vm = tcpr.find(W + "vMerge")
    return vm is not None and vm.get(W + "val") is None


def _table_bands_pt(tbl, styles: Styles, params) -> List[Tuple[float, bool]]:
    """回 [(带高磅, 该带有没有字)]。

    纵向合并的处理：续格所在的行与它上面那行之间没有横线，渲染出来是一条双高的带，PyMuPDF 的
    find_tables 也就把它们读成一行。所以这里把被 vMerge 连起来的相邻行并成一条带，带高 = 成员行高之和，
    与真渲量到的是同一个量。不并带则四件合并单元格模板行高低估 34%～51%，方向危险（#55）。
    """
    grid = _grid_widths(tbl)
    ml, mr, mt, mb = _cell_margins(tbl)
    rows = []
    joins = []  # 第 i 行是否与第 i-1 行连成一带
    for tr in tbl.findall(W + "tr"):
        col = 0
        cell_h, has_text = [], False
        joins.append(any(_is_vmerge_continuation(tc) for tc in tr.findall(W + "tc")))
        for tc in tr.findall(W + "tc"):
            tcpr = tc.find(W + "tcPr")
            span = 1
            if tcpr is not None:
                gs = tcpr.find(W + "gridSpan")
                if gs is not None:
                    try:
                        span = int(gs.get(W + "val"))
                    except (TypeError, ValueError):
                        span = 1
            width = sum(grid[col:col + span]) if grid else 0
            col += span
            avail = max(width - ml - mr, 1)
            h = 0.0
            for p in tc.findall(W + "p"):
                ph, t = _para_height_pt(p, styles, avail, params)
                h += ph
                has_text = has_text or t
            cell_h.append(h)
        rh = (max(cell_h) if cell_h else 0.0) + _tw2pt(mt + mb)
        trpr = tr.find(W + "trPr")
        if trpr is not None:
            th = trpr.find(W + "trHeight")
            if th is not None:
                try:
                    v = _tw2pt(int(th.get(W + "val")))
                except (TypeError, ValueError):
                    v = None
                if v is not None:
                    rh = v if th.get(W + "hRule") == "exact" else max(rh, v)
        rows.append((rh, has_text))

    bands = []
    for i, (rh, ht) in enumerate(rows):
        if i and joins[i] and bands:
            prev_h, prev_t = bands[-1]
            bands[-1] = (prev_h + rh, prev_t or ht)
        else:
            bands.append((rh, ht))
    return bands


def _estimate_once(doc: Docx, params) -> Dict[str, object]:
    """按一组参数走一遍版面：回页数、空白页、最大行高及其坐标。"""
    styles = Styles(doc.styles_root())
    body_tw, page_h_tw = doc.section_metrics()
    body_tw = max(body_tw, 1)
    page_h_pt = max(_tw2pt(page_h_tw), 1.0)
    pages = [{"used": 0.0, "text": False, "row": 0.0, "at": ""}]

    def newpage():
        pages.append({"used": 0.0, "text": False, "row": 0.0, "at": ""})

    def place(h, has_text, at):
        """整块放置：表格的一条带不拆页。"""
        cur = pages[-1]
        if cur["used"] + h > page_h_pt + 1e-6 and cur["used"] > 0:
            newpage()
            cur = pages[-1]
        cur["used"] += h
        cur["text"] = cur["text"] or has_text
        if at and h > cur["row"]:
            cur["row"], cur["at"] = h, at

    def place_paragraph(lines, lh, before, after, has_text):
        """按行拆页放一个正文段落：Word 在行边界上拆段，整段挪走会每段浪费一次。"""
        left = max(lines, 1)
        head = before
        while left > 0:
            cur = pages[-1]
            room = page_h_pt - cur["used"] - head
            fit = int(room // lh + 1e-9) if lh > 0 else left
            if fit <= 0:
                if cur["used"] <= 0:
                    fit = 1  # 空页也放不下一行（行高大于版心）：硬放一行，免得死循环
                else:
                    newpage()
                    head = 0.0
                    continue
            take = min(fit, left)
            cur["used"] += head + take * lh
            cur["text"] = cur["text"] or has_text
            left -= take
            head = 0.0
            if left > 0:
                newpage()
        pages[-1]["used"] += after

    table_no = 0
    for block in doc.body:
        if block.tag == W + "p":
            if _has_page_break(block):
                newpage()
            place_paragraph(*_para_layout(block, styles, body_tw, params))
        elif block.tag == W + "tbl":
            table_no += 1
            for row_no, (rh, has_text) in enumerate(_table_bands_pt(block, styles, params), 1):
                place(rh, has_text, "第 %d 张表第 %d 行" % (table_no, row_no))

    tallest, where = 0.0, ""
    for i, p in enumerate(pages, 1):
        if p["row"] > tallest:
            tallest, where = p["row"], "第 %d 页%s" % (i, p["at"])
    return {"页数": len(pages), "空白页": [i for i, p in enumerate(pages, 1) if not p["text"]],
            "最大行高": tallest, "最大行高位置": where}


def estimate_ranges(doc: Docx) -> Dict[str, object]:
    """三项几何判据的推算区间。空白页折成「空白页数」这个量，阈值恒为 0，与另两项同一个判定式。"""
    lo = _estimate_once(doc, ESTIMATE_BOUNDS["lo"])
    hi = _estimate_once(doc, ESTIMATE_BOUNDS["hi"])
    k_lo, k_hi, pad = ROW_HEIGHT_TOLERANCE
    row_lo = round(lo["最大行高"] * k_lo, 1)
    row_hi = round(hi["最大行高"] * k_hi + pad, 1)
    blank_lo, blank_hi = set(lo["空白页"]), set(hi["空白页"])
    certain = sorted(blank_lo & blank_hi)
    possible = sorted(blank_lo | blank_hi)
    raw_lo = min(lo["页数"], hi["页数"])
    page_lo = max(1, raw_lo - int(round(raw_lo * PAGE_LOW_MARGIN)))
    return {
        "页数": (page_lo, max(lo["页数"], hi["页数"], page_lo)),
        "最大行高": (min(row_lo, row_hi), max(row_lo, row_hi)),
        "最大行高位置": hi["最大行高位置"] or lo["最大行高位置"] or "全篇",
        "空白页": (len(certain), len(possible)),
        "空白页坐标": possible,
        "必空页": certain,
    }


# ---------------------------------------------------------------- 渲染层（机会性加信，可选依赖）

def render_pdf(docx_path: pathlib.Path, powershell: Optional[str]) -> Tuple[pathlib.Path, pathlib.Path]:
    """Word COM 经 powershell.exe 子进程导出 PDF；返回 (pdf 路径, 临时目录)。

    任何一步不成都是 NoRender 而不是错误：主力环境（mac + WPS）上没有渲染通道是正常路径（ADR-0017）。
    """
    exe = shutil.which(powershell or "powershell.exe")
    if not exe:
        raise NoRender("找不到 %s" % (powershell or "powershell.exe"))
    base = pathlib.Path(tempfile.gettempdir()) / TEMP_DIRNAME
    base.mkdir(parents=True, exist_ok=True)
    while True:
        work = base / secrets.token_hex(4)
        try:
            os.mkdir(work)  # 不用 mkdtemp：它建的目录 ACL 只有三条，别的账户写不了
            break
        except FileExistsError:
            continue
    pdf = work / (docx_path.stem + ".pdf")
    script = PS_RENDER.replace("{IN}", str(docx_path.resolve()).replace("'", "''")).replace("{OUT}", str(pdf).replace("'", "''"))
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    cmd = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]
    first = ""
    for attempt in range(2):  # Word 偶发瞬时失败（导出报错、实例被别的会话关掉），整个再起一次
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        except subprocess.TimeoutExpired:
            shutil.rmtree(work, ignore_errors=True)
            raise NoRender("Word 导出超过 120 秒没有回来")
        out = (r.stdout or "").strip()
        if r.returncode == 0 and pdf.is_file():
            return pdf, work
        first = out.splitlines()[0] if out else ((r.stderr or "").strip().splitlines() or ["退出码 %d" % r.returncode])[0]
        if first.startswith("NOWORD"):
            break  # 起不来 Word 不是瞬时故障
    shutil.rmtree(work, ignore_errors=True)
    raise NoRender("Word COM 没能出 PDF（%s）" % first)


def _page_body_text(page) -> str:
    """页面正文的字：底边一英寸内、只像页码的字块当页脚去掉（正文最后一行可能贴着页脚，不能只按位置切）。"""
    height = page.rect.height
    parts = []
    for block in page.get_text("blocks", sort=True):
        y0, text = block[1], block[4]
        if y0 >= height - FOOTER_ZONE and PAGE_NUMBER_ONLY.match(text.strip() or ""):
            continue
        parts.append(text)
    return "".join(parts)


def render_measure(pdf: pathlib.Path, doc: Docx) -> Dict[str, object]:
    """读渲出来的 PDF，取三项几何点值与两条渲染侧披露项。PyMuPDF 只在这里 import（可选依赖）。"""
    try:
        import pymupdf
    except ImportError as e:
        raise NoRender("没装 PyMuPDF（%s）" % e)
    if hasattr(pymupdf, "no_recommend_layout"):
        pymupdf.no_recommend_layout()  # 否则 find_tables 往 stdout 印一行推荐语，污染 --json
    try:
        pdfdoc = pymupdf.open(str(pdf))
    except Exception as e:
        raise NoRender("PDF 打不开（%s）" % e)
    notes: List[str] = []
    blank: List[int] = []
    fonts = set()
    rendered = []
    tallest, where = 0.0, ""
    for i, page in enumerate(pdfdoc, 1):
        body = _page_body_text(page)
        rendered.append(re.sub(r"\s+", "", body))
        if not body.strip() and not page.get_images():
            blank.append(i)
        for f in page.get_fonts():
            fonts.add(f[3].split("+")[-1])
        for table_no, t in enumerate(page.find_tables().tables, 1):
            for row_no, row in enumerate(t.rows, 1):
                h = row.bbox[3] - row.bbox[1]
                if h > tallest:
                    tallest, where = h, "第 %d 页第 %d 张表第 %d 行" % (i, table_no, row_no)
    embedded = sorted(fonts)
    requested = doc.requested_fonts()
    missing = [f for f in requested if not _font_embedded(f, embedded)]
    if missing:
        notes.append("请求字体不在嵌入字体里：%s（嵌入：%s）" % ("、".join(missing), "、".join(embedded) or "无"))
    # PDF 里的字块顺序与段落不一一对应（表格里并排的格会交错），所以只比字的多重集：
    # 一个段落或单元格的字在渲出的字里凑不齐，就是有字没渲出来。
    pool = Counter("".join(rendered))
    lost = []
    for chunk in doc.text_chunks():
        need = Counter(chunk)
        if all(pool[ch] >= n for ch, n in need.items()):
            pool.subtract(need)
        else:
            lost.append(chunk)
    if lost:
        notes.append("有字没渲出来（多半是固定行高裁掉了）：%s" % "、".join(c[:12] for c in lost[:6]))
    return {"页数": len(pdfdoc), "空白页": blank, "最大行高": round(tallest, 1),
            "最大行高位置": where or "全篇", "披露项": notes}


def _norm_font(name: str) -> str:
    key = re.sub(r"[\s\-_]", "", name).lower()
    key2 = re.sub(r"[\s\-]", "", name).lower()
    return FONT_ALIASES.get(key2, FONT_ALIASES.get(key, key))


def _font_embedded(requested: str, embedded: List[str]) -> bool:
    want = _norm_font(requested)
    for e in embedded:
        have = re.sub(r"[\s\-_,]", "", e).lower()
        if have.startswith(want) or want.startswith(have):
            return True
    return False


# ---------------------------------------------------------------- 三档判定

CRITERIA_UNIT = {"页数": "页", "空白页": "页", "最大行高": "磅"}


def _verdict(lo: float, hi: float, threshold: float) -> str:
    """ADR-0017 的判定式：T < lo 不通过；T >= hi 通过；lo <= T < hi 需人眼。点值即 lo == hi，恒为二值。

    阈值这一侧一点缓冲都不加，ADR-0017 明令「不加缓冲带」并逐条否掉了它。区间本身有多宽是另一回事：
    那是推算模型自己的不确定度（`ESTIMATE_BOUNDS` 两组参数加两条量测容差），住在推算层里，不是在这里
    对同一个不确定性再收一次费。
    """
    if threshold < lo:
        return "不通过"
    if threshold >= hi:
        return "通过"
    return "需人眼"


def _num(name: str, v: float) -> str:
    return ("%.1f" % v) if name == "最大行高" else ("%d" % round(v))


def _span(name: str, lo: float, hi: float, measured: bool) -> str:
    """实测的写点值，推算的一律带「推算」二字：区间收成一个数时也不能读成量出来的。"""
    unit = CRITERIA_UNIT[name]
    if measured:
        return "%s %s" % (_num(name, lo), unit)
    if lo == hi:
        return "推算 %s %s" % (_num(name, lo), unit)
    return "推算 %s～%s %s" % (_num(name, lo), _num(name, hi), unit)


def _pages_text(pages: List[int]) -> str:
    return "第 %s 页" % "、".join(str(p) for p in pages)


def _reading(name: str, ranges: Dict[str, object], render: Optional[Dict[str, object]]) -> Tuple[float, float, str, List[int]]:
    """一项判据在这一次门禁里的读数：(下界, 上界, 坐标, 空白页码)。

    有渲染结果时点值取代推算区间（回来的 lo == hi），坐标与空白页码也随之换成实测的那一份。
    """
    if name == "空白页":
        lo, hi = ranges["空白页"]
        if render is None:
            return lo, hi, _pages_text(ranges["空白页坐标"]), ranges["必空页"]
        pages = render["空白页"]
        return len(pages), len(pages), _pages_text(pages) if pages else "无", pages
    lo, hi = ranges[name]
    seat = ranges["最大行高位置"] if name == "最大行高" else "全篇"
    if render is None:
        return lo, hi, seat, []
    if name == "最大行高":
        seat = render["最大行高位置"]
    return render[name], render[name], seat, []


def judge(ranges: Dict[str, object], render: Optional[Dict[str, object]], max_pages: int,
          max_row_height: float) -> Dict[str, List[str]]:
    """三项几何判据的三档判定。回一份四类项的清单：不通过项、需人眼项、披露项、须目验清单的行、
    推算区间不含实测值。

    点值落在推算区间外时结论仍以点值为准，另出一条固定名披露项，它的唯一读者是开发者（ADR-0017）。
    """
    fails: List[str] = []
    needs: List[str] = []
    notes: List[str] = []
    checklist: List[str] = []
    outliers: List[str] = []
    thresholds = {"页数": float(max_pages), "空白页": 0.0, "最大行高": float(max_row_height)}
    measured = render is not None

    for name in ("页数", "空白页", "最大行高"):
        band_lo, band_hi = ranges[name]
        lo, hi, seat, blank_pages = _reading(name, ranges, render)
        if measured and not band_lo <= lo <= band_hi:
            outliers.append("推算区间不含实测值：%s，实测 %s %s，推算区间 %s～%s %s"
                            % (name, _num(name, lo), CRITERIA_UNIT[name], _num(name, band_lo),
                               _num(name, band_hi), CRITERIA_UNIT[name]))
        threshold = thresholds[name]
        verdict = _verdict(lo, hi, threshold)
        if verdict == "不通过":
            if name == "页数":
                fails.append("页数超阈值：%s，阈值 %d 页" % (_span(name, lo, hi, measured), max_pages))
            elif name == "空白页":
                fails.append("空白页：%s" % _pages_text(blank_pages))
            else:
                fails.append("行高超阈值：%s %s（阈值 %s 磅）" % (seat, _span(name, lo, hi, measured), _num(name, max_row_height)))
        elif verdict == "需人眼":
            needs.append("%s测不准：%s，阈值 %s %s" % (name, _span(name, lo, hi, measured), _num(name, threshold),
                                                CRITERIA_UNIT[name]))
            checklist.append("- %s：%s；%s，阈值 %s %s；最坏越界 %s %s"
                             % (name, seat, _span(name, lo, hi, measured), _num(name, threshold), CRITERIA_UNIT[name],
                                _num(name, hi - threshold), CRITERIA_UNIT[name]))

    if render is None:
        notes.append("页数：%s" % _span("页数", ranges["页数"][0], ranges["页数"][1], False))
    else:
        notes.append("页数：%d" % render["页数"])
    return {"不通过项": fails, "需人眼项": needs, "披露项": notes,
            "须目验清单": checklist, "推算区间不含实测值": outliers}


def format_checklist(lines: List[str]) -> str:
    """须目验清单：结论为需人眼时审查报告的第一段。固定格式，由门禁生成，不由模型撰写（ADR-0017）。"""
    if not lines:
        return ""
    return "\n".join(["须目验清单"] + lines + ["确认前请在 WPS 或 Word 里打开看这几处。"])


# ---------------------------------------------------------------- 门禁与落盘

def run_gate(docx_path: pathlib.Path, template_path: Optional[pathlib.Path], max_pages: int, max_row_height: float,
             powershell: Optional[str], no_render: bool = False) -> Dict[str, object]:
    doc = Docx(docx_path)
    template = Docx(template_path) if template_path else None
    fails, notes = static_checks(doc, template)
    try:
        ranges = estimate_ranges(doc)
    except Exception as e:  # 推算层是门禁本体，它自己挂了才是「门禁跑不动」
        raise CannotRun("推算层抛异常：%s：%s" % (type(e).__name__, e))

    render = None
    reason = "按 --no-render 跳过"
    if not no_render:
        try:
            pdf, work = render_pdf(docx_path, powershell)
            try:
                render = render_measure(pdf, doc)
            finally:
                shutil.rmtree(work, ignore_errors=True)
        except NoRender as e:
            reason = str(e)
    if render is None:
        notes.append("无渲染结果：页数、空白页、最大行高按版面推算给出区间（%s）" % reason)
    else:
        notes += render["披露项"]

    verdicts = judge(ranges, render, max_pages, max_row_height)
    needs = verdicts["需人眼项"]
    outliers = verdicts["推算区间不含实测值"]
    fails += verdicts["不通过项"]
    notes += verdicts["披露项"] + outliers
    if template is None:
        notes.append("未给 --template：没查页脚 PAGE 域丢失、模板说明段残留与模板表缺失")
    conclusion = "不通过" if fails else ("需人眼" if needs else "通过")
    return {
        "文件": str(docx_path),
        "结论": conclusion,
        "不通过项": fails,
        "需人眼项": needs,
        "披露项": notes,
        # 清单只在整件结论是需人眼时出：不通过件根本不落盘，也就没有那份审查报告（ADR-0017）
        "须目验清单": format_checklist(verdicts["须目验清单"]) if conclusion == "需人眼" else "",
        "页数": None if render is None else render["页数"],
        "推算": {"页数": list(ranges["页数"]), "空白页": list(ranges["空白页"]), "最大行高": list(ranges["最大行高"]),
                "空白页坐标": ranges["空白页坐标"], "最大行高位置": ranges["最大行高位置"]},
        "渲染": None if render is None else {"页数": render["页数"], "空白页": render["空白页"],
                                          "最大行高": render["最大行高"], "最大行高位置": render["最大行高位置"]},
        "推算区间不含实测值": outliers,
    }


def deliver(src: pathlib.Path, target: pathlib.Path) -> None:
    if target.exists():
        raise Refused("目标已存在，不覆盖：%s（成品仍在 %s）" % (target, src))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(target))


def format_report(result: Dict[str, object]) -> str:
    lines = []
    if result["须目验清单"]:
        lines.append(result["须目验清单"])
        lines.append("")
    lines.append("版式门禁：%s" % result["结论"])
    lines.append("不通过项：" + ("无" if not result["不通过项"] else ""))
    for f in result["不通过项"]:
        lines.append("- " + f)
    if result["需人眼项"]:
        lines.append("需人眼项：")
        for n in result["需人眼项"]:
            lines.append("- " + n)
    lines.append("披露项：")
    for n in result["披露项"]:
        lines.append("- " + n)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="gate.py", description="版式门禁：静态检查加版面推算，有渲染时以渲染加信；只读，不合格不落盘。")
    ap.add_argument("docx", help="要检查的文书（.docx）")
    ap.add_argument("--template", help="该节点的官方模板，给了才查页脚 PAGE 域丢失、模板说明段残留与模板表缺失")
    ap.add_argument("--deliver", help="通过与需人眼两档把文书一次性拷到这个路径（已存在则拒绝）")
    ap.add_argument("--json", action="store_true", help="结果按 JSON 打印")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="页数阈值，默认 %(default)s")
    ap.add_argument("--max-row-height", type=float, default=DEFAULT_MAX_ROW_HEIGHT, help="表格行高阈值（磅），默认 %(default)s")
    ap.add_argument("--powershell", help="powershell.exe 的路径，默认从 PATH 找")
    ap.add_argument("--no-render", action="store_true", help="不起渲染层，只用门禁本体（推算层）给结论")
    return ap


EXIT_CODES = {"通过": 0, "不通过": 1, "需人眼": 3}


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    docx_path = pathlib.Path(args.docx)
    template = pathlib.Path(args.template) if args.template else None
    try:
        if not docx_path.is_file():
            raise CannotRun("文书不存在：%s" % docx_path)
        if template is not None and not template.is_file():
            raise CannotRun("模板不存在：%s" % template)
        result = run_gate(docx_path, template, args.max_pages, args.max_row_height, args.powershell, args.no_render)
    except CannotRun as e:
        sys.stderr.write("门禁无法运行：%s\n" % e)
        return 2
    delivered = None
    refused = None
    if result["结论"] in ("通过", "需人眼") and args.deliver:
        try:
            deliver(docx_path, pathlib.Path(args.deliver))
            delivered = str(pathlib.Path(args.deliver))
        except Refused as e:
            refused = str(e)
    if args.json:
        print(json.dumps(dict(result, 已落盘=delivered, 落盘被拒=refused), ensure_ascii=False, indent=2))
    else:
        print(format_report(result))
        if delivered:
            print("已落盘 %s" % delivered)
        if result["结论"] == "不通过" and args.deliver:
            print("未落盘：门禁不通过")
    for line in result["推算区间不含实测值"]:
        sys.stderr.write(line + "\n")
    if refused:
        sys.stderr.write("门禁无法运行：落盘被拒：%s\n" % refused)
        return 2
    return EXIT_CODES[result["结论"]]


if __name__ == "__main__":
    sys.exit(main())
