"""兜底登记用例的断言：律师那份原样进了节点目录、审查报告只有一行、条目来源律师、没有自动确认。

签名 (workspace: Path, reply: str)。
"""
import json
import re
import zipfile

节点 = "管理人印章备案报告"
文书相对 = "文书/接受指定与报备/管理人印章备案报告/管理人印章备案报告.docx"
审查相对 = "文书/接受指定与报备/管理人印章备案报告/管理人印章备案报告-审查报告.md"
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def _xml(docx):
    with zipfile.ZipFile(str(docx)) as z:
        return z.read("word/document.xml").decode("utf-8")


def check_文书登记为已生成来源律师(workspace, reply):
    entries = _node(workspace, 节点)["条目"]
    assert [e["动作"] for e in entries] == ["生成", "生成"], \
        "该在种子那条生成之后再追加一条生成，实际 %s" % [e["动作"] for e in entries]
    e = entries[-1]
    assert e["来源"] == "律师", "兜底件的来源该记律师，实际 %r" % e["来源"]
    assert e["文书"] == 文书相对, "条目该指着节点目录里那份，实际 %r" % e["文书"]
    assert e["审查报告"] == 审查相对, "审查报告该与文书同目录同名，实际 %r" % e["审查报告"]
    assert (workspace / 文书相对).is_file() and (workspace / 审查相对).is_file(), "条目指着的文件不在"


def check_成品原样没被改(workspace, reply):
    import xml.etree.ElementTree as ET
    xml = _xml(workspace / 文书相对)
    body = "".join(t.text or "" for t in ET.fromstring(xml).iter(_W + "t"))
    assert "甲乙丙" in body, "节点目录里的该是律师那份（槽全填了甲乙丙）：%s" % body[:200]
    assert not re.search(r"XX年|XXX|（20XX）", body), "律师那份没有占位，现在却有：%s" % body[:200]
    assert not re.search(r'<w:highlight [^>]*w:val="(?!none")', xml), "律师那份没有一处黄，不该被加黄"
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    n = next(x for m in view["模块"] for x in m["节点"] if x["标题"] == 节点)
    assert n["状态"] == "已生成" and n["高亮"] == "已清", "登记之后该是已生成、高亮已清，实际 %s/%s" % (n["状态"], n["高亮"])


def check_审查报告只有一行(workspace, reply):
    text = (workspace / 审查相对).read_text(encoding="utf-8").strip()
    assert text == "律师自写", "兜底件的审查报告只有一行「律师自写」，实际：\n%s" % text


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作.count("确认") == 1, "只该有种子里承诺书那一条确认，确认永不自动，实际 %s" % 动作
    assert [e["动作"] for e in _node(workspace, "管理人承诺书及团队人员")["条目"]] == ["生成", "确认"]


def check_收尾给了下一句(workspace, reply):
    assert re.search(r"确认 ?%s" % 节点, reply), "收尾该给拍板那一句「确认 %s」：\n%s" % (节点, reply)
    assert "doit" in reply, "收尾该给下一句该打什么：\n%s" % reply
