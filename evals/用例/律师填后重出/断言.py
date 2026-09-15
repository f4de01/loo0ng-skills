"""律师填后重出用例的断言：点名处填了、律师填过的只去黄或不碰、插的段在、条目两条、审查报告重写、律师说过的多一行。

签名 (workspace: Path, reply: str)。文书用 fill.py 自己的原语读（段落、高亮区间、槽），与出件那一侧同一把尺。
"""
import importlib.util
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[3]
FILL = REPO / "skills" / "in-progress" / "to-docx" / "scripts" / "fill.py"
节点 = "管理人印章备案报告"
文书相对 = "文书/接受指定与报备/管理人印章备案报告/管理人印章备案报告.docx"
审查相对 = "文书/接受指定与报备/管理人印章备案报告/管理人印章备案报告-审查报告.md"
补记 = "律师补记：印模以刻章回执为准。"
公安局 = "甲市公安局乙分局"
种子里的三行 = ("受理裁定是甲年乙月丙日作的", "管理人是丙律师事务所", "章是甲年乙月丙日刻的")

_spec = importlib.util.spec_from_file_location("loo0ng_fill_for_assert", FILL)
填 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(填)


def _paragraphs(workspace):
    import docx
    doc = docx.Document(str(workspace / 文书相对))
    return [(填.text_of(p), 填.highlight_ranges(p), 填.slots(p)) for p in 填.paragraphs(doc)]


def _only(paras, text):
    hits = [x for x in paras if x[0] == text]
    assert len(hits) == 1, "文书里该恰有一段是「%s」，实际 %d 段" % (text, len(hits))
    return hits[0]


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def check_点名处填了不再黄(workspace, reply):
    text, hl, _ = next(x for x in _paragraphs(workspace) if "公安局" in x[0])
    assert "甲市公安局" in text, "律师在对话里给了公安局名，该填进去：%s" % text
    assert "XXX" not in text, "公安局名的占位该被填掉：%s" % text
    assert hl == [], "点名处照改、改完不加黄：仍有高亮 %s" % (hl,)


def check_律师填了留黄的只去黄(workspace, reply):
    text, hl, _ = _only(_paragraphs(workspace), "甲年乙月丙日")
    assert hl == [], "律师填了没去黄的启用时间，模型该只去黄：仍有高亮 %s" % (hl,)


def check_律师填了去黄的不碰(workspace, reply):
    text, hl, _ = _only(_paragraphs(workspace), "甲年乙月丁日")
    assert hl == [], "律师填了又去了黄的落款日期，一个字不碰、也不重新加黄：%s" % (hl,)


def check_律师插的段原样在(workspace, reply):
    paras = _paragraphs(workspace)
    text, hl, _ = _only(paras, 补记)
    assert hl == [], "律师插的段不该被加黄"
    i = [x[0] for x in paras].index(补记)
    assert paras[i + 1][0].startswith("苏州工业园区人民法院于"), "插的段该还在正文第一段之前：后一段是「%s」" % paras[i + 1][0][:20]


def check_文书下仍只有这一份(workspace, reply):
    files = [p.relative_to(workspace).as_posix() for p in (workspace / "文书").rglob("*.docx")]
    assert files == [文书相对], "重出覆盖同一份，文书/ 下该只有它：%s" % files


def check_条目两条生成(workspace, reply):
    entries = _node(workspace, 节点)["条目"]
    assert [e["动作"] for e in entries] == ["生成", "生成"], "重出该在种子那条生成之后再追加一条，实际 %s" % [e["动作"] for e in entries]
    assert entries[-1]["来源"] == "agent" and entries[-1]["文书"] == 文书相对, "新条目不对：%s" % entries[-1]
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert "确认" not in 动作, "重出不是确认：%s" % 动作


def check_审查报告重写(workspace, reply):
    text = (workspace / 审查相对).read_text(encoding="utf-8")
    for heading in ("## 生成依据", "## 高亮清单", "## 施加原话", "## 时限"):
        assert heading in text, "审查报告缺固定段 %s：\n%s" % (heading, text)
    assert re.search(r"高亮清单 \d+ 处", text), "高亮清单段该照抄这一版 apply 的回显：\n%s" % text
    清单 = text.split("## 高亮清单", 1)[1].split("## 施加原话", 1)[0]
    assert "「XXX」" not in 清单, "公安局那处这一版填掉了，高亮清单该是这一版的、不该还记着它：\n%s" % 清单


def check_律师说过的多一行(workspace, reply):
    行 = [l for l in (workspace / "材料" / "律师说过的.md").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(行) >= len(种子里的三行), \
        "这份文件只追加、原有三行一字不动，现在只剩 %d 行：%s" % (len(行), 行)
    for i, 原 in enumerate(种子里的三行):
        assert 原 in 行[i], "原有第 %d 行该一字不动：%r" % (i + 1, 行[i])
    新 = 行[3:]
    assert 新 and any("公安局" in l for l in 新), "律师在对话里说的公安局该追加成一行：%s" % 新
    assert all(re.search(r"\d{4}-\d{2}-\d{2}", l) for l in 新), "追加的每一行要带日期：%s" % 新
