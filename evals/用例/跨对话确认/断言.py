"""跨对话确认用例的断言：确认直接落条目、没重出、别的节点没动、收尾只说下一个节点。签名 (workspace: Path, reply: str)。"""
import json
import re

确认的 = "管理人印章备案报告"
文书相对 = "文书/接受指定与报备/管理人印章备案报告/管理人印章备案报告.docx"


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def check_确认直接落了没重出(workspace, reply):
    entries = _node(workspace, 确认的)["条目"]
    动作 = [e["动作"] for e in entries]
    assert 动作 == ["生成", "确认"], "新对话里说确认该直接落条目、不重出，实际 %s" % 动作
    assert entries[-1]["来源"] == "律师", "确认的来源恒为律师"
    words = entries[-1].get("原话", "")
    assert "确认" in words or "填完" in words, "原话该是律师那句话，实际 %r" % words
    assert (workspace / 文书相对).is_file(), "文书该还在原处"


def check_别的节点没动(workspace, reply):
    assert [e["动作"] for e in _node(workspace, "管理人银行账户备案报告")["条目"]] == ["生成"], "银行账户备案不该被动"
    assert [e["动作"] for e in _node(workspace, "管理人承诺书及团队人员")["条目"]] == ["生成", "确认"], "承诺书不该被动"
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert sorted(动作) == sorted(["生成", "确认", "生成", "生成", "确认"]), "图上多出了别的条目：%s" % 动作


def check_视图算成已确认(workspace, reply):
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    n = next(x for m in view["模块"] for x in m["节点"] if x["标题"] == 确认的)
    assert n["状态"] == "已确认", "视图该把它算成已确认，实际 %r" % n["状态"]


def check_收尾只说下一个节点(workspace, reply):
    """收尾第三段拍板之后只剩第二行（doit 的 SKILL.md「收尾三段」）：不再回头请律师拍板这个节点。

    那一行恒在：`前方` 非空时它是 `doit 出一版 <前方第一个>`，不许拿一句「去问 ask-loo0ng」顶替。
    这个种子整份起手 72 节点、三个已生成，前方剩 69 个，第一个是同模块的「管理人工作计划」
    （不按时限改序），所以第一条断言硬断那条命令本身：只查「新对话」或「doit」在不在，
    「不知道下一个办什么就打 ask-loo0ng」那种收尾照样能过，而它正是正文要消灭的形态。

    别拿「高亮了哪几处」当反面判据：那是收尾第二段的小标题，拍板这一回合照样要有（写「这一回合没有出件」）。
    """
    assert re.search(r"doit\s*出一版\s*[`「『\"']*\s*管理人工作计划", reply), (
        "拍板之后收尾该给出能直接打的那条命令 `doit 出一版 管理人工作计划`（前方第一个）：\n%s" % reply)
    assert "本节点拍板" not in reply, "拍板之后收尾第三段只剩「下一个节点开新对话」那一行：\n%s" % reply
    assert not re.search(r"要不要确认|请你?确认一下|是否要确认", reply), "确认已落，不再问第二句：\n%s" % reply
