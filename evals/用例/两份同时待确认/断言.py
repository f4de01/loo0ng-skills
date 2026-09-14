"""路由用例「两份同时待确认」的断言：当前节点是复数、先确认哪一份、不因时限改序。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序)

先 = "管理人印章备案报告"
后 = "管理人银行账户备案报告"
要生成的 = "管理人工作计划"
带时限但排在后面的 = ("内部管理制度备案报告", "刻制管理人公章的申请")
带时限的节点 = 先
时限 = "自收到《刻制管理人公章函》之日起 3 日内刻制管理人公章，交法院封样备案后启用（手册，法院要求）"


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "有两份待确认，该命中问 1：\n%s" % reply


def check_两份都列出来了(workspace, reply):
    s = 段(reply, "三问")
    assert s.strip(), "回复里没有「三问」这一段：\n%s" % reply
    for 节点 in (先, 后):
        assert 节点 in s, "「三问」里没列出待确认的「%s」：\n%s" % (节点, s)


def check_下一句是图里靠前的那一份(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 确认 %s" % (前缀, 先)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)
    尾 = reply[reply.rfind("下一句该打什么"):]
    assert 后 not in 尾, "下一句该是图里靠前的那一份，不是「%s」：\n%s" % (后, 尾)


def check_时限原样附上(workspace, reply):
    s = 段(reply, "往下的路")
    assert 时限 in s, \
        "「%s」在领域图上带时限句，往下的路里该原样附上（ADR-0016）：\n%s" % (带时限的节点, s)


def check_不因时限改序(workspace, reply):
    s = 段(reply, "往下的路") + 段(reply, "三问")
    assert 要生成的 in s, \
        "待确认之后要生成的该是案件图里最早的未生成节点「%s」：\n%s" % (要生成的, s)
    for 节点 in 带时限但排在后面的:
        if 节点 in s:
            assert s.index(要生成的) < s.index(节点), \
                "「%s」带时限但在图里排在「%s」后面，路由不该因时限把它提前：\n%s" % (节点, 要生成的, s)
