"""起手用例的断言：目录形状、图与两份视图、指针块、归档去向、归档索引、既有成品登记、没有自动确认、收尾五行。

签名 (workspace: Path, reply: str)。
"""
import json
import pathlib
import re

目录 = ["待归档", "材料", "参考/模板", "参考/指南", "文书"]
根上允许 = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "归档索引.md", "待归档", "材料", "参考", "文书"}
成品 = "管理人承诺书（已交法院）.md"
成品节点 = "管理人承诺书及团队人员"
成品落点 = "文书/接受指定与报备/管理人承诺书及团队人员/管理人承诺书及团队人员.md"
包内 = "skills/in-progress/domain/assets"    # 指针块不该指进这里：包一升级它就被换掉


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _nodes(data):
    for m in data["模块"]:
        for n in m["节点"]:
            yield m, n


def _node(workspace, title):
    for _, n in _nodes(_graph(workspace)):
        if n["标题"] == title:
            return n
    raise AssertionError("图里没有节点「%s」" % title)


def check_目录形状(workspace, reply):
    for rel in 目录:
        assert (workspace / rel).is_dir(), "缺格 %s" % rel
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    多 = [n for n in names if n not in 根上允许]
    assert not 多, "工作区根多出了东西：%s" % 多


def check_图整份拷入(workspace, reply):
    data = _graph(workspace)
    assert set(data) == {"格式版本", "模块"}, "图顶层多了键：%s" % sorted(data)
    assert len(data["模块"]) == 12, "预设图「破产」12 个模块该整份进图，实际 %d" % len(data["模块"])
    titles = [n["标题"] for _, n in _nodes(data)]
    assert len(titles) == 72, "72 个节点该整份进图，实际 %d" % len(titles)
    assert len(titles) == len(set(titles)), "图里有重名节点"
    for name in ("图视图.md", "图视图.json"):
        assert (workspace / name).is_file(), "缺视图 %s" % name
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    assert view["格式版本"] == data["格式版本"], "两份 JSON 的格式版本应一致"
    模板 = sorted(p.name for p in (workspace / "参考" / "模板").iterdir() if p.suffix == ".docx")
    assert len(模板) == 19, "预设图的 19 件空白模板该整份拷进 参考/模板/，实际 %d：%s" % (len(模板), 模板)


def check_指针块只记名与归属(workspace, reply):
    agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
    assert "预设图：破产（出厂）" in agents, "指针块该记「预设图：破产（出厂）」：\n%s" % agents
    assert 包内 not in agents.replace("\\", "/"), "指针块不记路径（ADR-0023），却指进了包内：\n%s" % agents
    assert not re.search(r"[A-Za-z]:[\\/]|/Users/|/home/", agents), "指针块里出现了绝对路径：\n%s" % agents
    for expected in ("图.json", "图视图.md", "图视图.json", "doit", "只读"):
        assert expected in agents, "指针块里缺 %s：\n%s" % (expected, agents)
    assert (workspace / "CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md", \
        "CLAUDE.md 只该有一行 @AGENTS.md"


def check_各归其格(workspace, reply):
    去向 = {
        "材料/债务人移交物品清单.txt": "本案事实来源原件",
        "参考/指南/甲法院破产案件管理人工作提示.md": "本案适用的官方要求文件",
        "参考/模板/（格式）债权申报登记表.md": "官方发布的空白件",
        "参考/模板/本所自用-接管物品交接单空表.md": "自己做的空白件也是空白件，归模板",
    }
    for rel, why in 去向.items():
        assert (workspace / rel).is_file(), "%s 没到 %s" % (why, rel)
    索引 = (workspace / "归档索引.md").read_text(encoding="utf-8")
    for rel in 去向:
        assert rel in 索引, "归档索引里没有 %s：\n%s" % (rel, 索引)


def check_拿不准的留在待归档(workspace, reply):
    left = sorted(p.name for p in (workspace / "待归档").rglob("*") if not _is_harness_noise(p.name))
    assert left == ["未命名.txt"], "待归档里该只剩那件没有正向证据的，实际 %s" % left


def check_既有成品登记为已生成来源律师(workspace, reply):
    entries = _node(workspace, 成品节点)["条目"]
    assert len(entries) == 1, "该节点应恰有一条条目，实际 %s" % entries
    e = entries[0]
    assert e["动作"] == "生成", "起手登记该是生成条目，实际 %r" % e["动作"]
    assert e["来源"] == "律师", "既有成品的来源该记律师，实际 %r" % e["来源"]
    assert e["文书"] == 成品落点, "既有成品该挪进节点的文书目录，实际 %r" % e["文书"]
    assert (workspace / e["文书"]).is_file(), "条目指着的文书不在：%s" % e["文书"]
    review = workspace / e["审查报告"]
    assert review.is_file(), "每一版文书必有一份审查报告，缺 %s" % e["审查报告"]
    assert review.read_text(encoding="utf-8").strip() == "律师自写", "既有成品的审查报告只有一行「律师自写」"
    assert not list(workspace.rglob(成品)), "登记之后原件不该还留在别处"


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for _, n in _nodes(_graph(workspace)) for e in n["条目"]]
    assert 动作 == ["生成"], "起手只该落那一条生成条目，确认永不自动，实际 %s" % 动作


# 收尾第一段那五行（SKILL.md「收尾三段」）：逐样查，报红时指名漏了哪一样。
第一段逐样 = (
    ("目录与图", r"目录与图|目录形状"),
    ("起手图", r"起手图|预设图"),
    ("待归档", r"待归档"),
    ("归档", r"归档[：:]|材料 ?\d+ ?件|归档了"),
    ("既有成品", r"既有成品|%s|%s" % (成品节点, re.escape(成品))),
)


def check_收尾第一段逐样说清(workspace, reply):
    缺 = [名 for 名, pat in 第一段逐样 if not re.search(pat, reply)]
    assert not 缺, "收尾第一段这几样一个字都没提：%s（正文的五行骨架一行不少）：\n%s" % ("、".join(缺), reply)


def check_收尾第三段给下一句(workspace, reply):
    assert re.search(r"doit", reply), "收尾第三段没给下一句该打什么：\n%s" % reply
