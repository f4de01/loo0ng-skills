"""路由用例「律师自加节点与改标题」的断言：按现在的标题称呼，靠 id 仍查得出时限。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序)

现在的标题 = "承诺书"
改之前的标题 = "管理人承诺书及团队人员"
律师自加的 = "补充材料说明"
带时限的节点 = 现在的标题
时限 = "自收到指定管理人决定书之日起 3 日内组建工作团队进驻债务人企业，并将团队情况向法院报备（手册，法院要求）"


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "有一份在等拍板，该命中问 1：\n%s" % reply


def check_下一句用现在的标题(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 确认 %s" % (前缀, 现在的标题)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)
    assert "确认 %s" % 改之前的标题 not in reply, \
        "标题已被律师改过，整串该用现在的标题「%s」：\n%s" % (现在的标题, reply)


def check_自加的节点排在领域图候选之前(workspace, reply):
    s = 段(reply, "三问") + 段(reply, "往下的路")
    assert 律师自加的 in s, \
        "案件图里已有的未生成节点（律师自加的「%s」）排在领域图候选之前，是问 2：\n%s" % (律师自加的, s)


def check_改了标题仍按id查出时限(workspace, reply):
    assert 时限 in reply, "改标题不动 id，领域图上那句时限仍该按 id 查出并原样附上：\n%s" % reply
