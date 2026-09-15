"""记一句用例的断言：律师顺口给的事实填进了文书、追加进了律师说过的.md、两件落盘、条目一条。

签名 (workspace: Path, reply: str)。

只断开户日期这一个值：模板 1-3 的账户三格是空单元格，既没有占位符也没有原文，五种差量都写不进去，
所以开户行与账户名称这一版落不进文书（见 用例.json 的说明）。开户日期那一处是真槽，判据靠它。
"""
import json
import re
import zipfile

节点 = "管理人银行账户备案报告"
文书相对 = "文书/接受指定与报备/管理人银行账户备案报告/管理人银行账户备案报告.docx"
审查相对 = "文书/接受指定与报备/管理人银行账户备案报告/管理人银行账户备案报告-审查报告.md"
开户日期 = "甲年乙月丁日"      # p3#1 与 p18#1 两个槽：开立日期与落款日期，律师这一句把两处都给了
种子里的四行 = ("受理裁定是甲年乙月丙日作的", "管理人是丙律师事务所",
             "指定管理人决定书是甲年乙月丙日收到的", "先把印章备案办完再动账户")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def _body(docx):
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(str(docx)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return "".join(t.text or "" for t in root.iter(_W + "t"))


def check_事实填进了文书(workspace, reply):
    assert (workspace / 文书相对).is_file(), "文书该落在 %s" % 文书相对
    body = _body(workspace / 文书相对)
    assert 开户日期 in body, "律师说的开户日期该填进 p3#1 那个槽：%s" % body[:300]
    assert "XX年X月X日开立" not in body, "开户日期填了，那一处不该还是原占位：%s" % body[:300]
    assert body.count(开户日期) >= 2, "律师说落款也写这一天，p18#1 那个槽也该填：%s" % body[:300]


def check_追加进了律师说过的(workspace, reply):
    行 = [l for l in (workspace / "材料" / "律师说过的.md").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(行) >= len(种子里的四行), \
        "这份文件只追加、原有四行一字不动，现在只剩 %d 行：%s" % (len(行), 行)
    for i, 原 in enumerate(种子里的四行):
        assert 原 in 行[i], "原有第 %d 行该一字不动：%r" % (i + 1, 行[i])
    新 = 行[4:]
    assert 新, "律师说的那句该追加成新的一行"
    assert any(开户日期 in l for l in 新), "追加的行里该有原话（含「%s」）：%s" % (开户日期, 新)
    assert all(re.search(r"\d{4}-\d{2}-\d{2}", l) for l in 新), "追加的每一行要带日期：%s" % 新


def check_两件落盘条目一条(workspace, reply):
    assert (workspace / 审查相对).is_file(), "审查报告该落在 %s" % 审查相对
    entries = _node(workspace, 节点)["条目"]
    assert [e["动作"] for e in entries] == ["生成"], "该恰有一条生成条目，实际 %s" % [e["动作"] for e in entries]
    assert entries[0]["文书"] == 文书相对, "条目该指着 %s，实际 %r" % (文书相对, entries[0]["文书"])


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作.count("确认") == 1, "只该有种子里承诺书那一条确认，实际 %s" % 动作
