"""种子「填过黄」：一份出过件的文书，律师在 Word 里动过三处、前面插了一段（#14）。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）

按出厂预设图「破产」起手（走真的起手 CLI）。agent 对节点「管理人印章备案报告」出过一版：能填的都填了
（值来自 材料/律师说过的.md），三处没材料留黄：公安局名（p3 的「XXX」）、启用时间（表里的「XX年X月X日」）、
落款日期（末尾的「XX年X月X日」）；审查报告按四段写，高亮清单是 apply 回显原话。图上有那条生成条目。

之后律师在 Word 里：启用时间填了「甲年乙月丙日」**没去黄**；落款日期填了「甲年乙月丁日」**去了黄**；
公安局名**没动**；在正文第一段之前**插了一段**「律师补记：印模以刻章回执为准。」。
律师的这几笔用 fill.py 的原语直接改 run 文字、不经差量，与 Word 里手改留下的 XML 同形。

供用例「模型误去黄」（律师一句「重出」，断的是模型判对了哪处是律师填的）与「律师填后重出」
（律师填过之后又在对话里补一个事实，据此重出）。
不含隐私检查器五类正则能命中的值：当事人、法院一律写「甲」「乙」「丙」，没有案号、手机号、身份证、
统一社会信用代码、案件目录路径。
"""
import importlib.util
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 回放助手 as 助手  # noqa: E402

模板名 = "1-2.关于管理人印章备案的报告.docx"
节点 = "管理人印章备案报告"
补记 = "律师补记：印模以刻章回执为准。"

律师说过的 = """2026-09-12 受理裁定是甲年乙月丙日作的，申请人甲公司，债务人乙公司，简称乙公司。
2026-09-12 管理人是丙律师事务所，负责人丁某。
2026-09-13 章是甲年乙月丙日刻的，两枚，公安局哪家我回头查。
"""

# 一张表：槽、填的值、来源；差量与审查报告的「生成依据」都从它派生，改值只改这里。
填值 = [
    ("p2#1", "甲年乙月丙日", "2026-09-12「受理裁定是甲年乙月丙日作的」"),
    ("p2#2", "（甲）", "2026-09-12「受理裁定是甲年乙月丙日作的」"),
    ("p2#3", "乙", "2026-09-12「受理裁定是甲年乙月丙日作的」"),
    ("p2#4", "甲", "2026-09-12「申请人甲公司」"),
    ("p2#5", "乙", "2026-09-12「债务人乙公司」"),
    ("p2#6", "乙", "2026-09-12「简称乙公司」"),
    ("p2#7", "（甲）", "2026-09-12「管理人是丙律师事务所」"),
    ("p2#8", "丙", "2026-09-12「管理人是丙律师事务所」"),
    ("p2#9", "丙律师事务所", "2026-09-12「管理人是丙律师事务所」"),
    ("p2#10", "乙", "2026-09-12「债务人乙公司」"),
    ("p2#11", "丁某", "2026-09-12「负责人丁某」"),
    ("p3#1", "甲年乙月丙日", "2026-09-13「章是甲年乙月丙日刻的」"),
    ("p3#3", "乙", "2026-09-12「债务人乙公司」"),
    ("p3#4", "乙", "2026-09-12「债务人乙公司」"),
    ("p13#1", "乙", "2026-09-12「债务人乙公司」"),
]
差量 = [{"op": "fill", "at": at, "text": text} for at, text, _ in 填值]
生成依据 = "".join("- %s「%s」← 材料/律师说过的.md %s\n" % (at, text, 来源) for at, text, 来源 in 填值)


def load_fill():
    spec = importlib.util.spec_from_file_location("loo0ng_fill_for_seed", 助手.FILL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def 出一版(ws):
    """agent 那一版：差量施加到 文书/，审查报告四段，图上追加生成条目。"""
    文书相对, 审查相对 = 助手.文书路径(ws, 节点)
    with tempfile.TemporaryDirectory() as tmp:
        diff = pathlib.Path(tmp) / "差量.json"
        diff.write_text(json.dumps(差量, ensure_ascii=False), encoding="utf-8")
        echo = 助手.run(ws, 助手.FILL, "apply", pathlib.Path("参考") / "模板" / 模板名, "--diff", diff, "--out", 文书相对)
    lines = echo.splitlines()
    head = next(i for i, l in enumerate(lines) if l.startswith("高亮清单 "))
    施加原话 = "\n".join(lines[:head])
    高亮清单 = "\n".join(lines[head:])
    出件环境 = lines[1]
    报告 = ("# 关于管理人印章备案的报告 审查报告\n\n## 生成依据\n\n%s- %s\n\n## 高亮清单\n\n%s\n\n"
            "## 施加原话\n\n%s\n\n## 时限\n\n规则：自收到《刻制管理人公章函》之日起 3 日内刻制管理人公章，"
            "交法院封样备案后启用（手册，法院要求）\n基准日：缺失\n推算截止日：基准日缺失，算不出\n"
            % (生成依据, 出件环境, 高亮清单, 施加原话))
    (ws / 审查相对).write_text(报告, encoding="utf-8")
    助手.引擎(ws, "generate", "--node", 节点, "--doc", 文书相对, "--review", 审查相对)
    return 文书相对


def 律师动手(ws, 文书相对):
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
    助手.引擎(ws, "views")   # 视图按律师动过之后的文书重算


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True
    ws = pathlib.Path(workspace)
    助手.起手(ws, 助手.破产)
    (ws / "材料" / "律师说过的.md").write_text(律师说过的, encoding="utf-8")
    文书相对 = 出一版(ws)
    律师动手(ws, 文书相对)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
