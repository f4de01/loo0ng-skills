"""tests/loo0ng-to-docx 的公用件：定位仓库、模板目录与两个 CLI，跑子进程，读 DOCX 里的 XML。

模板目录：官方模板原件住领域目录 skills/productivity/loo0ng-domain/assets/破产/模板/（ADR-0004、ADR-0009，#29）。找不到就直接报错，不 skip。
"""
import json
import pathlib
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "skills" / "productivity" / "loo0ng-to-docx" / "scripts"
CONVERTER = SCRIPTS / "md2docx.py"
GATE = SCRIPTS / "gate.py"
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
PROBE_TEMPLATE = "1-2.关于管理人印章备案的报告.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"


def templates_dir() -> pathlib.Path:
    templates = REPO / "skills" / "productivity" / "loo0ng-domain" / "assets" / "破产" / "模板"
    if (templates / PROBE_TEMPLATE).is_file():
        return templates
    raise AssertionError("找不到官方模板目录 %s" % templates)


def template(prefix: str) -> pathlib.Path:
    """按文件名前缀（如 "1-2."）找一件官方模板。"""
    hits = sorted(p for p in templates_dir().glob("*.docx") if p.name.startswith(prefix))
    if len(hits) != 1:
        raise AssertionError("模板前缀 %s 命中 %d 件" % (prefix, len(hits)))
    return hits[0]


def all_templates():
    return sorted(templates_dir().glob("*.docx"))


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


def run(script, *args) -> Run:
    r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return Run(r.returncode, r.stdout, r.stderr)


def convert(markdown: str, tpl: pathlib.Path, out: pathlib.Path) -> Run:
    md = out.with_suffix(".md")
    md.write_text(markdown, encoding="utf-8")
    return run(CONVERTER, md, "--template", tpl, "--out", out)


def gate(docx: pathlib.Path, *extra) -> Run:
    """跑门禁并解析 --json 的结果，挂在 Run.result 上；退出码 2（门禁跑不动、落盘被拒）时 result 为 None。

    三档结论对应退出码 0 通过 / 3 需人眼 / 1 不通过（ADR-0017），三档都出 JSON。
    """
    r = run(GATE, docx, "--json", *extra)
    r.result = json.loads(r.out) if r.out.strip().startswith("{") else None
    return r


def gate_no_render(docx: pathlib.Path, *extra) -> Run:
    """无渲染跑道：只用门禁本体（推算层）。主力环境（mac + WPS）恒定走这条，任何机器上都跑得动。"""
    return gate(docx, "--no-render", *extra)


_RENDER_PROBE = {}


def render_available() -> bool:
    """本机有没有渲染通道。整个进程只探一次（一次门禁约 7 秒）。"""
    if "ok" not in _RENDER_PROBE:
        r = gate(templates_dir() / PROBE_TEMPLATE)
        _RENDER_PROBE["ok"] = bool(r.result and r.result.get("渲染"))
    return _RENDER_PROBE["ok"]


def require_render(case) -> None:
    """渲染层测试专用的门：拿不到渲染通道就 skip，且打印一行说明、不静默。

    推算层是门禁本体、永远在，跑推算层的测试在任何机器上必须全绿、不许 skip；只有明确测「渲染器接上时
    的行为」这几件许 skip（ADR-0017 改了 ADR-0015 的口径）。
    """
    if not render_available():
        reason = "本机没有渲染通道（ADR-0017：这是主力环境的正常路径，不是故障），跳过渲染层这一件"
        print("SKIP %s：%s" % (case.id(), reason))
        case.skipTest(reason)


def read_xml(docx: pathlib.Path, member: str = "word/document.xml"):
    with zipfile.ZipFile(str(docx)) as z:
        return ET.fromstring(z.read(member))


def rewrite(src: pathlib.Path, dst: pathlib.Path, edits) -> pathlib.Path:
    """按成员名改写 DOCX 里的部件：edits 是 {成员名: fn(bytes) -> bytes}。构造故障件用。"""
    with zipfile.ZipFile(str(src)) as zin, zipfile.ZipFile(str(dst), "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in edits:
                data = edits[item.filename](data)
            zout.writestr(item, data)
    return dst


def text_of(el) -> str:
    return "".join(t.text or "" for t in el.iter(W + "t"))


def body_blocks(docx: pathlib.Path):
    body = read_xml(docx).find(W + "body")
    return [c for c in body if c.tag in (W + "p", W + "tbl")]


def table_signature(tbl):
    """表的形：列宽、每行行高、每格 (gridSpan, vMerge)。同形 = 签名相等。"""
    grid = [g.get(W + "w") for g in tbl.find(W + "tblGrid").findall(W + "gridCol")]
    rows = []
    for tr in tbl.findall(W + "tr"):
        trpr = tr.find(W + "trPr")
        h = trpr.find(W + "trHeight") if trpr is not None else None
        height = (h.get(W + "val"), h.get(W + "hRule")) if h is not None else None
        cells = []
        for tc in tr.findall(W + "tc"):
            tcpr = tc.find(W + "tcPr")
            span = tcpr.find(W + "gridSpan") if tcpr is not None else None
            vm = tcpr.find(W + "vMerge") if tcpr is not None else None
            cells.append((span.get(W + "val") if span is not None else "1",
                          (vm.get(W + "val") or "continue") if vm is not None else None))
        rows.append((height, tuple(cells)))
    return (tuple(grid), tuple(rows))


def markdown_mirroring(tpl: pathlib.Path) -> str:
    """给一件模板合成一份甲乙丙占位稿：正文几段，每张表与模板同形（合并按约定用 < 与 ^ 占位）。"""
    lines = ["# 甲乙丙报告", "", ":left: 甲法院：", "",
             "甲法院于甲年乙月丙日作出裁定，裁定受理乙公司破产清算一案，并指定本所担任管理人。", "",
             "现将有关情况报告如下，请予审查。", ""]
    body = read_xml(tpl).find(W + "body")
    for tbl in body.findall(W + "tbl"):
        ncols = len(tbl.find(W + "tblGrid").findall(W + "gridCol"))
        for tr in tbl.findall(W + "tr"):
            cells = []
            for tc in tr.findall(W + "tc"):
                tcpr = tc.find(W + "tcPr")
                span = tcpr.find(W + "gridSpan") if tcpr is not None else None
                vm = tcpr.find(W + "vMerge") if tcpr is not None else None
                n = int(span.get(W + "val")) if span is not None else 1
                first = "^" if (vm is not None and vm.get(W + "val") is None) else "甲"
                cells.append(first)
                cells.extend(["<"] * (n - 1))
            assert len(cells) == ncols, "%s 的表行格数 %d 与列数 %d 不符" % (tpl.name, len(cells), ncols)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
        lines.append("以上表格照模板所列。")
        lines.append("")
    lines += ["特此报告", "", ":right: 乙公司管理人", ":right: 甲年乙月丙日", ""]
    return "\n".join(lines)


def strip_ws(s: str) -> str:
    return re.sub(r"\s+", "", s)
