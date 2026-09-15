"""出一版留黄用例的断言：开场清了待归档、两件落盘、填了材料有的、缺的留黄、审查报告四段、条目一条、收尾三段。

签名 (workspace: Path, reply: str)。
"""
import json
import re
import zipfile

节点 = "管理人银行账户备案报告"
文书相对 = "文书/接受指定与报备/管理人银行账户备案报告/管理人银行账户备案报告.docx"
审查相对 = "文书/接受指定与报备/管理人银行账户备案报告/管理人银行账户备案报告-审查报告.md"
指南 = "甲法院破产案件管理人工作提示.md"
根上允许 = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "归档索引.md", "待归档", "材料", "参考", "文书"}
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


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


def check_开场清了待归档(workspace, reply):
    assert (workspace / "参考" / "指南" / 指南).is_file(), "开场该把待归档里那份指南归进 参考/指南/"
    left = sorted(p.name for p in (workspace / "待归档").rglob("*") if not _is_harness_noise(p.name))
    assert left == [], "开场清待归档之后该是空的，实际 %s" % left
    索引 = (workspace / "归档索引.md").read_text(encoding="utf-8")
    assert ("参考/指南/" + 指南) in 索引, "归档索引里该多出那份指南的一行：\n%s" % 索引


def check_两件落盘(workspace, reply):
    assert (workspace / 文书相对).is_file(), "文书该落在 %s" % 文书相对
    assert (workspace / 审查相对).is_file(), "审查报告该落在 %s" % 审查相对
    files = sorted(p.relative_to(workspace).as_posix() for p in (workspace / "文书").rglob("*.docx"))
    assert files.count(文书相对) == 1 and len(files) == 3, "文书/ 下该是种子的两件加这一件，实际 %s" % files


def check_填了材料有的_骨架还在(workspace, reply):
    body = _body(workspace / 文书相对)
    assert "乙公司" in body, "材料里有债务人乙公司，该填进去：%s" % body[:200]
    for 骨架 in ("特此报告", "开户银行", "苏州工业园区人民法院"):
        assert 骨架 in body, "模板骨架里的「%s」不该被改掉：%s" % (骨架, body[:300])


def check_缺的留黄(workspace, reply):
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    n = next(x for m in view["模块"] for x in m["节点"] if x["标题"] == 节点)
    assert n["状态"] == "已生成", "出一版之后该是已生成，实际 %r" % n["状态"]
    assert n["高亮"] == "未清", "账户信息材料里没有，那几处该留黄（引擎的高亮列该是 未清），实际 %r" % n["高亮"]


def check_审查报告四段(workspace, reply):
    text = (workspace / 审查相对).read_text(encoding="utf-8")
    for heading in ("## 生成依据", "## 高亮清单", "## 施加原话", "## 时限"):
        assert heading in text, "审查报告缺固定段 %s：\n%s" % (heading, text)
    assert re.search(r"高亮清单 \d+ 处", text), "高亮清单段该照抄 apply 回显的「高亮清单 N 处」：\n%s" % text
    assert "出件环境" in text, "生成依据末条该是出件环境那一行：\n%s" % text
    assert "已写出" in text, "施加原话段该照抄 apply 回显：\n%s" % text


def check_生成条目一条(workspace, reply):
    entries = _node(workspace, 节点)["条目"]
    assert [e["动作"] for e in entries] == ["生成"], "该恰有一条生成条目，实际 %s" % [e["动作"] for e in entries]
    e = entries[0]
    assert e["来源"] == "agent", "出一版的来源该是 agent，实际 %r" % e["来源"]
    assert e["文书"] == 文书相对 and e["审查报告"] == 审查相对, "条目里的两条路径不对：%s" % e


def check_别的节点与律师说过的没动(workspace, reply):
    assert [e["动作"] for e in _node(workspace, "管理人印章备案报告")["条目"]] == ["生成"]
    assert [e["动作"] for e in _node(workspace, "管理人承诺书及团队人员")["条目"]] == ["生成", "确认"]
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作.count("确认") == 1, "确认永不自动，实际 %s" % 动作
    行 = [l for l in (workspace / "材料" / "律师说过的.md").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(行) == 4, "律师这一句没给事实，律师说过的.md 该还是四行，实际 %d 行" % len(行)


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    多 = [n for n in names if n not in 根上允许]
    assert not 多, "工作区根多出了东西（差量与中间件写临时位置）：%s" % 多
    stray = [p.name for p in (workspace / 文书相对).parent.iterdir() if p.suffix not in (".docx", ".md")]
    assert stray == [], "文书目录里多出了东西：%s" % stray


def check_收尾三段(workspace, reply):
    assert re.search(r"高亮|黄", reply), "收尾该说高亮了哪几处：\n%s" % reply
    assert re.search(r"确认 ?%s|%s 不适用" % (节点, 节点), reply), "收尾该给拍板那一句：\n%s" % reply
    assert "doit" in reply, "收尾该给下一句该打什么：\n%s" % reply
