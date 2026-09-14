#!/usr/bin/env python3
"""原型驱动：对包内 19 件模板把六个问题跑一遍，结果打在 stdout，docx 只落临时目录。
用法：python demo.py <输出目录>
测试内容全部合成：当事人「某某公司」，案号的年份填「（某年）」、序号填「1」，拼不出真案号的形状。"""
import copy
import importlib.util
import json
import pathlib
import sys

import docx
from docx.oxml.ns import qn

import fill

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
TEMPLATES = sorted((REPO / "skills/in-progress/domain/assets/破产/模板").glob("*.docx"))
GATE = REPO / "skills/in-progress/to-docx/scripts/gate.py"
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def load_gate():
    spec = importlib.util.spec_from_file_location("gate", str(GATE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def short(t):
    return t.stem.split(".")[0]


def section(title):
    print("\n" + "=" * 8 + " " + title)


# ---------------------------------------------------------------- 1 打清单
section("1 打清单（19 件）")
total_slots = 0
for t in TEMPLATES:
    d = docx.Document(str(t))
    text = fill.listing(d)
    (OUT / (short(t) + ".清单.txt")).write_text(text, encoding="utf-8")
    n_slots = sum(len(fill.slots(p)) for p in fill.paragraphs(d))
    n_note = sum(1 for p in fill.paragraphs(d) if fill.NOTE.match(fill.text_of(p)))
    total_slots += n_slots
    print("%-8s 段 %3d  槽 %3d  说明段 %d" % (short(t), len(fill.paragraphs(d)), n_slots, n_note))
print("合计槽", total_slots)
print("\n--- 1-2 的清单原样：")
print(fill.listing(docx.Document(str(TEMPLATES[1]))))

# ---------------------------------------------------------------- 2 原地施加
section("2 原地施加：19 件各跑两遍（只留黄 / 全填），比几何与格式")
problems = []
for t in TEMPLATES:
    for mode in ("留黄", "全填"):
        d = docx.Document(str(t))
        geo0, fmt0 = fill.geometry_snapshot(d)
        text0 = [fill.text_of(p) for p in fill.paragraphs(d)]
        ops = []
        if mode == "全填":
            for i, p in enumerate(fill.paragraphs(d)):
                for n, _ in enumerate(fill.slots(p), 1):
                    ops.append({"op": "fill", "at": "p%d#%d" % (i, n), "text": "某某"})
        changed, log = fill.apply(d, ops, highlight_rest=True)
        geo1, fmt1 = fill.geometry_snapshot(d)
        if geo0 != geo1:
            problems.append("%s %s 表格几何变了" % (short(t), mode))
        # 改动段以外：字符格式逐个相同；改动段：槽以外的字符格式相同（按填前文本对齐）
        for i, p in enumerate(fill.paragraphs(d)):
            if mode == "留黄":
                if fmt0[i] != fmt1[i] or fill.text_of(p) != text0[i]:
                    problems.append("%s 留黄 p%d 文字或格式变了" % (short(t), i))
            else:
                # 全填：把填前每个槽外的字符的格式与填后对应位置比
                sl = [(s, e) for s, e, _ in fill.slots_of_text(text0[i])] if hasattr(fill, "slots_of_text") else \
                     [(m.start(), m.end()) for m in fill.PLACEHOLDER.finditer(text0[i])]
                pos0 = pos1 = 0
                for s, e in sl:
                    if fmt0[i][pos0:s] != fmt1[i][pos1:pos1 + (s - pos0)]:
                        problems.append("%s 全填 p%d 槽外格式变了" % (short(t), i))
                    pos1 += (s - pos0) + 2  # 「某某」两个字
                    pos0 = e
                if fmt0[i][pos0:] != fmt1[i][pos1:]:
                    problems.append("%s 全填 p%d 段尾格式变了" % (short(t), i))
        d.save(str(OUT / ("%s.%s.docx" % (short(t), mode))))
print("问题：", problems or "无")

print("\n--- 固定文字与槽混在一段（1-2 p2）：填前 / 填后的 run 与格式")
d = docx.Document(str(TEMPLATES[1]))
p = fill.paragraphs(d)[2]


def show_runs(p):
    for r in p.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        sz = rpr.find(qn("w:sz")).get(qn("w:val")) if rpr is not None and rpr.find(qn("w:sz")) is not None else "-"
        fonts = rpr.find(qn("w:rFonts")) if rpr is not None else None
        ea = fonts.get(qn("w:eastAsia")) if fonts is not None else "-"
        print("   [%s] sz=%s %s%s" % (fill.text_of(r), sz, ea, " 黄" if fill._is_hl(r) else ""))


show_runs(p)
fill.apply(d, [
    {"op": "fill", "at": "p2#1", "text": "2026年1月1日"},
    {"op": "fill", "at": "p2#2", "text": "（某年）"},
    {"op": "fill", "at": "p2#3", "text": "1"},
    {"op": "replace", "at": "p2", "old": "XX公司（债权人名称）", "new": "某甲公司"},
    {"op": "replace", "at": "p2", "old": "XX公司（债务人名称）（以下简称XX公司）", "new": "某某公司（以下简称某某公司）"},
    {"op": "fill", "at": "p2#8", "text": "2025", "highlight": True},
], highlight_rest=True)
print("   ----")
show_runs(p)
print("   清单行：", fill.listing(d).splitlines()[2])

print("\n--- 删段：正文段、单元格里唯一的段、表格所在行")
d = docx.Document(str(TEMPLATES[1]))
n_before = len(fill.paragraphs(d))
changed, log = fill.apply(d, [{"op": "delete", "at": "p14"}, {"op": "delete", "at": "p9"}], highlight_rest=False)
print("  ", log, "段数", n_before, "→", len(fill.paragraphs(d)))
geo_del, _ = fill.geometry_snapshot(d)
print("   表格几何与原模板相同：", geo_del == fill.geometry_snapshot(docx.Document(str(TEMPLATES[1])))[0])

# ---------------------------------------------------------------- 3 重出的比对
section("3 重出的比对（1-2：出件留黄 → 律师改两处 → 比对）")
d = docx.Document(str(TEMPLATES[1]))
changed, log = fill.apply(d, [
    {"op": "fill", "at": "p2#1", "text": "2026年1月1日"},
    {"op": "fill", "at": "p1", "text": "某某人民法院："},
], highlight_rest=True)
recorded = fill.record_highlights(d)
out1 = OUT / "1-2.出件.docx"
d.save(str(out1))
(OUT / "1-2.高亮清单.json").write_text(fill.dumps(recorded), encoding="utf-8")
print("高亮清单 %d 处，前三处：" % len(recorded))
for rec in recorded[:3]:
    print("  ", json.dumps(rec, ensure_ascii=False))

# 模拟律师在 Word 里改：p3 第一处填了字并去黄；p3 第二处填了字没去黄；另在最前面插一段、删 p10（特此报告）
d2 = docx.Document(str(out1))
ps = fill.paragraphs(d2)
p3 = ps[3]
hl = fill.highlight_ranges(p3)
fill.replace_range(p3, hl[0][0], hl[0][1], "2026年2月2日", False)   # 填了、去黄
hl = fill.highlight_ranges(p3)
fill.replace_range(p3, hl[0][0], hl[0][1], "某某", None)           # 填了、没去黄
new_p = copy.deepcopy(ps[10])
ps[0].addprevious(new_p)
fill.replace_range(new_p, 0, len(fill.text_of(new_p)), "律师自己加的一段", None)
fill.replace_range(new_p, 0, 2, None, True)   # 律师自己标黄「律师」两字
ps[10].getparent().remove(ps[10])
lawyer = OUT / "1-2.律师改过.docx"
d2.save(str(lawyer))

d3 = docx.Document(str(lawyer))
print("清单编号已飘（插了一段、删了一段）：p2 现在是「%s…」" % fill.text_of(fill.paragraphs(d3)[2])[:12])
for line in fill.compare(d3, recorded):
    print("  ", line)
d3.save(str(OUT / "1-2.重出底稿.docx"))

# ---------------------------------------------------------------- 4 门禁两样
section("4 门禁两样")
d = docx.Document(str(TEMPLATES[1]))
changed, _ = fill.apply(d, [{"op": "fill", "at": "p2#1", "text": "2026年1月1日"}], highlight_rest=False)
print("a) 只填一槽、不留黄 → check_changed：", fill.check_changed(d, changed))
d = docx.Document(str(TEMPLATES[1]))
changed, _ = fill.apply(d, [{"op": "fill", "at": "p2#1", "text": "2026年1月1日"}], highlight_rest=True)
print("   同样但留黄 → check_changed：", fill.check_changed(d, changed) or "通过")
gate = load_gate()
for name in ("1-2.全填.docx", "1-1.全填.docx", "1-2.出件.docx"):
    gd = gate.Docx(OUT / name)
    ranges = gate.estimate_ranges(gd)
    verdict = gate.judge(ranges, None, gate.DEFAULT_MAX_PAGES, gate.DEFAULT_MAX_ROW_HEIGHT)
    print("b) gate.estimate_ranges(%s)：页数 %s 最大行高 %s → 不通过项 %s 需人眼 %s" % (
        name, ranges["页数"], ranges["最大行高"], verdict["不通过项"], verdict["需人眼项"]))
    fails, notes = gate.static_checks(gd, gate.Docx(TEMPLATES[1] if name.startswith("1-2") else TEMPLATES[0]))
    print("   现有 static_checks 会报：", fails)

# ---------------------------------------------------------------- 6 版本
section("6 python 3.9 / python-docx 1.2.0")
import ast
ast.parse((HERE / "fill.py").read_text(encoding="utf-8"), feature_version=(3, 9))
print("fill.py 按 3.9 feature_version 解析通过；用到的 python-docx API：Document、Run.text、Run.font.highlight_color、"
      "BaseOxmlElement.xpath；其余是 lxml 与 re。运行时：python-docx", docx.__version__)
print("\n输出目录：", OUT)
