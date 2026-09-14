"""起手用例的断言：六格、图与两份视图、工作区指针块、归档去向、雏形、既有成品登记、没有自动确认。

签名 (workspace: Path, reply: str)。
"""
import json
import pathlib
import re

CELLS = ["收件箱", "材料", "材料/律师陈述", "指南", "模板/官方", "模板/生成", "文书"]
活图末尾 = "领域/破产"                      # ~/.loo0ng/领域/破产（ADR-0019）；eval 里 LOO0NG_HOME 指进临时目录
出厂种子 = "skills/in-progress/domain/assets"    # 指针块不该指进这里：包一升级它就被换掉
成品 = "管理人承诺书（已交法院）.md"
成品节点 = "管理人承诺书及团队人员"
新节点 = "联络人备案表"


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。

    #105 实测 Codex 也会把 uv 的缓存落成不带点的 `uv-cache`，所以 `uv-` 开头的一并忽略：
    它是 harness 自备解释器留下的，不是 skill 的产物。七份同名小函数逐字相同，改一处就一起改。
    """
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


def check_六格齐全(workspace, reply):
    for rel in CELLS:
        assert (workspace / rel).is_dir(), "缺格 %s" % rel
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
                     "指南", "收件箱", "文书", "材料", "模板"], "工作区根多出了东西：%s" % names


def check_图与两份视图都在(workspace, reply):
    data = _graph(workspace)
    assert set(data) == {"格式版本", "领域", "模块"}, "图顶层多了键：%s" % sorted(data)
    assert data["领域"] == "破产", "领域应是 破产，实际 %r" % data["领域"]
    for name in ("图视图.md", "图视图.json"):
        assert (workspace / name).is_file(), "缺视图 %s" % name
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    assert view["格式版本"] == data["格式版本"], "两份 JSON 的格式版本应一致"


def _领域目录(workspace):
    agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
    m = re.search(r"^- 领域目录：(\S+)\s*$", agents, re.M)
    assert m, "指针块缺领域目录：\n%s" % agents
    return m.group(1)


def check_工作区指针块四项齐全(workspace, reply):
    agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
    assert re.search(r"^- 领域：破产\s*$", agents, re.M), "指针块缺领域名：\n%s" % agents
    路径 = _领域目录(workspace)
    正斜杠 = 路径.replace("\\", "/")
    assert 正斜杠.endswith(活图末尾), \
        "领域目录应是活图 <家>/%s 的绝对路径（ADR-0019），实际 %r" % (活图末尾, 路径)
    assert 出厂种子 not in 正斜杠, \
        "领域目录指进了 skill 包内的出厂种子（%s）：包一升级律师累计的东西就被抹掉，" \
        "正是 ADR-0019 要挡的事故。活图路径由 sketch.py home 取，实际 %r" % (出厂种子, 路径)
    assert pathlib.Path(路径).is_absolute(), "领域目录要写绝对路径，实际 %r" % 路径
    for expected in ("图.json", "图视图.md", "图视图.json", "doit", "只读"):
        assert expected in agents, "指针块里缺 %s：\n%s" % (expected, agents)
    assert (workspace / "CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md", \
        "CLAUDE.md 只该有一行 @AGENTS.md"


def check_活图已经建起来(workspace, reply):
    """首次起手拷种子（ADR-0019）：指针块指到哪，那里就该有一份三样齐全的领域目录。"""
    live = pathlib.Path(_领域目录(workspace))
    assert live.is_dir(), "指针块指着的活图目录不存在：%s" % live
    有 = sorted(p.name for p in live.iterdir())
    assert (live / "领域图.json").is_file(), "活图里没有 领域图.json：%s" % 有
    assert (live / "模板").is_dir() and (live / "指引手册").is_dir(), \
        "活图该是出厂种子的整份副本（领域图.json、模板/、指引手册/）：%s" % 有


def check_收件箱各归其格(workspace, reply):
    去向 = {
        "材料/债务人移交物品清单.txt": "本案事实来源原件",
        "指南/甲法院破产案件管理人工作提示.md": "本案适用的官方要求文件",
        "模板/官方/（格式）债权申报登记表.md": "官方发布的空白件",
        "模板/生成/本所自用-接管物品交接单空表.md": "自己做的空白件",
        "材料/%s" % 成品: "既有成品，归材料",
    }
    for rel, why in 去向.items():
        assert (workspace / rel).is_file(), "%s 没到 %s" % (why, rel)


def check_拿不准的留在收件箱(workspace, reply):
    left = sorted(p.name for p in (workspace / "收件箱").rglob("*"))
    assert left == ["未命名.txt"], "收件箱里该只剩那件没有正向证据的，实际 %s" % left


def check_雏形写进了图(workspace, reply):
    data = _graph(workspace)
    titles = [n["标题"] for _, n in _nodes(data)]
    assert 成品节点 in titles, "指南里提到的「%s」没进图：%s" % (成品节点, titles)
    assert 新节点 in titles, "指南里提到的「%s」没进图：%s" % (新节点, titles)
    assert _node(workspace, 成品节点)["id"] == "n-chengnuoshu", "同名节点应按领域图带入、沿用领域图的 id"
    assert len(titles) == len(set(titles)), "图里有重名节点：%s" % titles
    assert len(titles) <= 6, "空图起手加一份指南不该长出这么多节点（惰性只约束 agent）：%s" % titles


def check_既有成品登记为已生成来源律师(workspace, reply):
    entries = _node(workspace, 成品节点)["条目"]
    assert len(entries) == 1, "该节点应恰有一条条目，实际 %s" % entries
    e = entries[0]
    assert e["动作"] == "生成", "起手登记该是生成条目，实际 %r" % e["动作"]
    assert e["来源"] == "律师", "既有成品的来源该记律师，实际 %r" % e["来源"]
    assert e["文书"] == "材料/%s" % 成品, "文书该指向归档后的既有成品，实际 %r" % e["文书"]
    review = workspace / e["审查报告"]
    assert review.is_file(), "每一版文书必有一份审查报告，缺 %s" % e["审查报告"]
    text = review.read_text(encoding="utf-8")
    for heading in ("## 生成依据", "## 存疑点", "## 待律师裁定", "## 版式门禁", "## 时限"):
        assert heading in text, "审查报告缺固定段 %s" % heading


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for _, n in _nodes(_graph(workspace)) for e in n["条目"]]
    assert 动作 == ["生成"], "起手只该落那一条生成条目，确认永不自动，实际 %s" % 动作


# 收尾第一段那五行（SKILL.md「收尾三段」）：逐样查，报红时指名漏了哪一样。
# 六条对五行：第一行「六格与图」两样都要，分开查才说得清漏的是哪一样（#65 漏的正是这两样）。
# 项名就是它真查的那个词：查的是这一样提没提，件数与节点名对不对由上面各条断言分别管。
第一段逐样 = (
    ("六格", r"六格"),
    ("图视图", r"图视图"),
    ("起手图", r"空图|整份起手|按指南起手|起手图"),
    ("归档", r"归档"),
    ("雏形", r"雏形"),
    ("既有成品", r"既有成品|%s|%s" % (成品节点, re.escape(成品))),
)


def check_收尾第一段逐样说清(workspace, reply):
    缺 = [名 for 名, pat in 第一段逐样 if not re.search(pat, reply)]
    assert not 缺, "收尾第一段这几样一个字都没提：%s（正文的五行骨架一行不少）：\n%s" % ("、".join(缺), reply)


def check_收尾第二段说该拍板什么(workspace, reply):
    assert re.search(r"确认|拍板", reply), "收尾第二段没说该拍板什么：\n%s" % reply


def check_收尾第三段给下一句(workspace, reply):
    assert re.search(r"doit", reply), "收尾第三段没给下一句该打什么：\n%s" % reply


def check_回显里出现过雏形与既有成品(workspace, reply):
    """AC「指南非空时回显含雏形」：起手清单是回显给律师的，从指南提出的那条与那件既有成品要在回复里看得见。"""
    assert 新节点 in reply, "回显里没有从指南提出的「%s」：\n%s" % (新节点, reply)
    assert 成品节点 in reply or 成品 in reply, "回显里没有既有成品的建议登记：\n%s" % reply
