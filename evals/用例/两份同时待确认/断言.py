"""路由用例「两份同时待确认」的断言：命中问 1、两份都列、下一句是靠前的那份、时限原样附上、不因时限改序。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

已清的 = "管理人印章备案报告"
未清的 = "管理人银行账户备案报告"
时限 = "自收到《刻制管理人公章函》之日起 3 日内刻制管理人公章，交法院封样备案后启用（手册，法院要求）"
前方第一 = "管理人工作计划"
排在后面带时限的 = ("内部管理制度备案报告", "刻制管理人公章的申请")


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "有一份黄色已清、等确认，该命中问 1：\n%s" % reply


def check_两份都列进当前节点(workspace, reply):
    s = 段(reply, "三问")
    assert s.strip(), "回复里没有「三问」这一段：\n%s" % reply
    for t in (已清的, 未清的):
        assert t in s, "两份同时待确认，「%s」该列进当前节点：\n%s" % (t, s)
    assert re.search(r"已清", s) and re.search(r"未清|还有黄|没清", s), "当前节点要逐份写明黄色清没清：\n%s" % s


def check_下一句是确认黄色已清的那份(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 确认 %s" % (前缀, 已清的)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


def check_时限原样附上(workspace, reply):
    assert 时限 in reply, "「%s」在图上带时限句，往下的路里该原样附上：\n%s" % (已清的, reply)


def check_要生成的是前方第一个不因时限改序(workspace, reply):
    s = 段(reply, "往下的路")
    assert re.search(r"出一版 ?%s" % 前方第一, s), "往下的路里要生成的该是前方第一个「%s」：\n%s" % (前方第一, s)
    for t in 排在后面带时限的:
        assert not re.search(r"出一版 ?%s" % t, s), "「%s」排在后面，不因它带时限就提前：\n%s" % (t, s)
