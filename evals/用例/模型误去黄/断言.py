"""用例「模型误去黄」的断言（#14）：律师填过的去黄不碰，没动的仍黄，插的段原样在，没有节点被自动确认。
签名 (workspace: Path, reply: str)。文书用 fill.py 自己的原语读（段落、高亮区间、槽），与出件那一侧同一把尺。"""
import importlib.util
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
FILL = REPO / "skills" / "in-progress" / "to-docx" / "scripts" / "fill.py"
文书相对 = "文书/接管/印章备案/印章备案.docx"
补记 = "律师补记：印模以刻章回执为准。"

_spec = importlib.util.spec_from_file_location("loo0ng_fill_for_assert", FILL)
填 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(填)


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def _paragraphs(workspace):
    import docx
    doc = docx.Document(str(workspace / 文书相对))
    return [(填.text_of(p), 填.highlight_ranges(p), 填.slots(p)) for p in 填.paragraphs(doc)]


def _only(paras, text):
    hits = [x for x in paras if x[0] == text]
    assert len(hits) == 1, "文书里该恰有一段是「%s」，实际 %d 段" % (text, len(hits))
    return hits[0]


def check_文书下恰一件docx(workspace, reply):
    files = sorted(p for p in (workspace / "文书").rglob("*.docx"))
    got = [p.relative_to(workspace).as_posix() for p in files]
    assert got == [文书相对], "重出覆盖同一份，文书/ 下该只有它：%s" % got


def check_没动的那处仍是黄且是原占位(workspace, reply):
    text, hl, sl = next(x for x in _paragraphs(workspace) if "公安局" in x[0])
    assert "XXX公安局" in text, "律师没动、也没材料的公安局名该还是原占位：%s" % text
    s, e, _ = next(x for x in sl if x[2] == "XXX")
    assert any(a <= s and e <= b for a, b in hl), "没动的占位该仍是黄的：%s" % text


def check_填了留黄的那处去黄且文字是律师填的(workspace, reply):
    text, hl, _ = _only(_paragraphs(workspace), "甲年乙月丙日")
    assert hl == [], "律师填了没去黄的启用时间，模型该只去黄：仍有高亮 %s" % (hl,)


def check_填了去黄的那处文字不动(workspace, reply):
    text, hl, _ = _only(_paragraphs(workspace), "甲年乙月丁日")
    assert hl == [], "律师填了又去了黄的落款日期，一个字不碰、也不重新加黄：%s" % (hl,)


def check_律师插的段原样在(workspace, reply):
    text, hl, _ = _only(_paragraphs(workspace), 补记)
    assert hl == [], "律师插的段不该被加黄"


def check_没有节点被自动确认(workspace, reply):
    data = json.loads((workspace / "图.json").read_text(encoding="utf-8"))
    entries = [e for m in data["模块"] for n in m["节点"] for e in n["条目"]]
    assert all(e["动作"] == "生成" for e in entries), "重出不是确认，条目里只该有生成：%s" % [e["动作"] for e in entries]


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    allowed = {"图.json", "图视图.json", "图视图.md", "待归档", "材料", "参考", "文书"}
    extra = [n for n in names if n not in allowed]
    assert extra == [], "工作区根多出了东西（差量写临时目录，工作区里不建暂存目录）：%s" % extra
    docs = workspace / "文书" / "接管" / "印章备案"
    stray = [p.name for p in docs.iterdir() if p.suffix not in (".docx", ".md")]
    assert stray == [], "文书目录里多出了东西：%s" % stray
