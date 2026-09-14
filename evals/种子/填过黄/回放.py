"""种子「填过黄」：一份出过件的文书，律师在 Word 里动过三处、前面插了一段（#14）。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）

一个模块一个节点（「接管」→「印章备案」，空白模板是官方模板 1-2），预设图由引擎自己造在临时目录、
整份拷入。agent 出过一版：能填的都填了（值来自 材料/律师说过的.md），三处没材料留黄：
公安局名（p3 的「XXX」）、启用时间（表里的「XX年X月X日」）、落款日期（末尾的「XX年X月X日」）；
审查报告按四段写，高亮清单是 apply 回显原话。图上有那条生成条目。

之后律师在 Word 里：启用时间填了「甲年乙月丙日」**没去黄**；落款日期填了「甲年乙月丁日」**去了黄**；
公安局名**没动**；在正文第一段之前**插了一段**「律师补记：印模以刻章回执为准。」。
律师的这几笔用 fill.py 的原语直接改 run 文字、不经差量，与 Word 里手改留下的 XML 同形。

供用例「模型误去黄」：律师一句「重出」，断的是模型判对了哪处是律师填的。
起手改由 skill "setup-case" 落（#17）之前，这里直接调引擎起图（目录形状照 ADR-0023）。
不含隐私检查器五类正则能命中的值：当事人、法院一律写「甲」「乙」「丙」，没有案号、手机号、身份证、
统一社会信用代码、案件目录路径。
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
ENGINE = REPO / "skills" / "in-progress" / "graph" / "scripts" / "graph.py"
FILL = REPO / "skills" / "in-progress" / "to-docx" / "scripts" / "fill.py"
TEMPLATE = REPO / "skills" / "in-progress" / "domain" / "assets" / "破产" / "模板" / "1-2.关于管理人印章备案的报告.docx"
目录 = ("待归档", "材料", "参考/模板", "参考/指南", "文书")
模块, 节点 = "接管", "印章备案"
文书相对 = "文书/接管/印章备案/印章备案.docx"
审查相对 = "文书/接管/印章备案/印章备案-审查报告.md"
补记 = "律师补记：印模以刻章回执为准。"

律师说过的 = """2026-09-12 受理裁定是甲年乙月丙日作的，申请人甲公司，债务人乙公司，简称乙公司。
2026-09-12 管理人是丙律师事务所，负责人丁某。
2026-09-13 章是甲年乙月丙日刻的，两枚，公安局哪家我回头查。
"""

差量 = [
    {"op": "fill", "at": "p2#1", "text": "甲年乙月丙日"},
    {"op": "fill", "at": "p2#2", "text": "（甲）"},
    {"op": "fill", "at": "p2#3", "text": "乙"},
    {"op": "fill", "at": "p2#4", "text": "甲"},
    {"op": "fill", "at": "p2#5", "text": "乙"},
    {"op": "fill", "at": "p2#6", "text": "乙"},
    {"op": "fill", "at": "p2#7", "text": "（甲）"},
    {"op": "fill", "at": "p2#8", "text": "丙"},
    {"op": "fill", "at": "p2#9", "text": "丙律师事务所"},
    {"op": "fill", "at": "p2#10", "text": "乙"},
    {"op": "fill", "at": "p2#11", "text": "丁某"},
    {"op": "fill", "at": "p3#1", "text": "甲年乙月丙日"},
    {"op": "fill", "at": "p3#3", "text": "乙"},
    {"op": "fill", "at": "p3#4", "text": "乙"},
    {"op": "fill", "at": "p13#1", "text": "乙"},
]

生成依据 = """- p2#1「甲年乙月丙日」← 材料/律师说过的.md 2026-09-12「受理裁定是甲年乙月丙日作的」
- p2#2「（甲）」← 材料/律师说过的.md 2026-09-12「受理裁定是甲年乙月丙日作的」
- p2#3「乙」← 材料/律师说过的.md 2026-09-12「受理裁定是甲年乙月丙日作的」
- p2#4「甲」← 材料/律师说过的.md 2026-09-12「申请人甲公司」
- p2#5「乙」← 材料/律师说过的.md 2026-09-12「债务人乙公司」
- p2#6「乙」← 材料/律师说过的.md 2026-09-12「简称乙公司」
- p2#7「（甲）」← 材料/律师说过的.md 2026-09-12「管理人是丙律师事务所」
- p2#8「丙」← 材料/律师说过的.md 2026-09-12「管理人是丙律师事务所」
- p2#9「丙律师事务所」← 材料/律师说过的.md 2026-09-12「管理人是丙律师事务所」
- p2#10「乙」← 材料/律师说过的.md 2026-09-12「债务人乙公司」
- p2#11「丁某」← 材料/律师说过的.md 2026-09-12「负责人丁某」
- p3#1「甲年乙月丙日」← 材料/律师说过的.md 2026-09-13「章是甲年乙月丙日刻的」
- p3#3「乙」← 材料/律师说过的.md 2026-09-12「债务人乙公司」
- p3#4「乙」← 材料/律师说过的.md 2026-09-12「债务人乙公司」
- p13#1「乙」← 材料/律师说过的.md 2026-09-12「债务人乙公司」
"""


def run(*args, cwd=None):
    r = subprocess.run([sys.executable] + [str(a) for a in args], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
        raise SystemExit(r.returncode)
    return r.stdout


def load_fill():
    spec = importlib.util.spec_from_file_location("loo0ng_fill_for_seed", FILL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def 起手(ws):
    for d in 目录:
        (ws / d).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        preset = pathlib.Path(tmp) / "印章"
        (preset / "模板").mkdir(parents=True)
        shutil.copy2(TEMPLATE, preset / "模板" / TEMPLATE.name)
        base = ["--graph", preset / "预设图.json", "--kind", "preset"]
        run(ENGINE, *base, "init", "--empty")
        run(ENGINE, *base, "add-module", "--title", 模块)
        run(ENGINE, *base, "add-node", "--module", 模块, "--title", 节点, "--template", TEMPLATE.name)
        run(ENGINE, "--graph", ws / "图.json", "init", "--preset", preset, cwd=ws)
    shutil.copy2(TEMPLATE, ws / "参考" / "模板" / TEMPLATE.name)
    (ws / "材料" / "律师说过的.md").write_text(律师说过的, encoding="utf-8")


def 出一版(ws):
    """agent 那一版：差量施加到 文书/，审查报告四段，图上追加生成条目。"""
    with tempfile.TemporaryDirectory() as tmp:
        diff = pathlib.Path(tmp) / "差量.json"
        diff.write_text(json.dumps(差量, ensure_ascii=False), encoding="utf-8")
        echo = run(FILL, "apply", pathlib.Path("参考") / "模板" / TEMPLATE.name, "--diff", diff, "--out", 文书相对, cwd=ws)
    lines = echo.splitlines()
    head = next(i for i, l in enumerate(lines) if l.startswith("高亮清单 "))
    施加原话 = "\n".join(lines[:head])
    高亮清单 = "\n".join(lines[head:])
    出件环境 = lines[1]
    报告 = ("# 关于管理人印章备案的报告 审查报告\n\n## 生成依据\n\n%s- %s\n\n## 高亮清单\n\n%s\n\n"
            "## 施加原话\n\n%s\n\n## 时限\n\n无明示时限\n" % (生成依据, 出件环境, 高亮清单, 施加原话))
    (ws / 审查相对).write_text(报告, encoding="utf-8")
    run(ENGINE, "--graph", ws / "图.json", "generate", "--node", 节点, "--doc", 文书相对, "--review", 审查相对, cwd=ws)


def 律师动手(ws):
    """律师在 Word 里的三笔加一段：改的是 run 里的字与 rPr，与手改同形。"""
    填 = load_fill()
    import docx
    from docx.text.paragraph import Paragraph
    path = ws / 文书相对
    doc = docx.Document(str(path))
    ps = 填.paragraphs(doc)
    启用时间 = next(p for p in ps if 填.text_of(p) == "XX年X月X日" and p.getparent().tag.endswith("}tc"))
    落款日期 = next(p for p in ps if 填.text_of(p) == "XX年X月X日" and not p.getparent().tag.endswith("}tc"))
    s, e, _ = 填.slots(启用时间)[0]
    填.replace_range(启用时间, s, e, "甲年乙月丙日", None)      # 填了、黄留着
    s, e, _ = 填.slots(落款日期)[0]
    填.replace_range(落款日期, s, e, "甲年乙月丁日", False)     # 填了、去了黄
    Paragraph(ps[2], None).insert_paragraph_before(补记)       # 正文第一段之前插一段
    doc.save(str(path))
    run(ENGINE, "--graph", ws / "图.json", "views", cwd=ws)   # 视图按律师动过之后的文书重算


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True
    ws = pathlib.Path(workspace)
    起手(ws)
    出一版(ws)
    律师动手(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
