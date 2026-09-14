"""路由用例「空图起手」的断言：空图上三问怎么答、命中哪一问、下一句整串。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序)

节点 = "管理人承诺书及团队人员"
带时限的节点 = 节点
时限 = "自收到指定管理人决定书之日起 3 日内组建工作团队进驻债务人企业，并将团队情况向法院报备（手册，法院要求）"


def check_命中问4(workspace, reply):
    assert re.search(r"命中问\s*4", reply), \
        "空图上问 1 至 3 都不成立，该命中问 4（领域图里还有案件图没有的节点）：\n%s" % reply


def check_没有待确认也没有上一完成(workspace, reply):
    s = 段(reply, "三问")
    assert s.strip(), "回复里没有「三问」这一段：\n%s" % reply
    当前 = [l for l in s.splitlines() if "当前节点" in l]
    上一 = [l for l in s.splitlines() if "上一完成" in l]
    assert 当前 and re.search(r"没有|无", 当前[0]), "空图上该答没有待确认的文书：%s" % 当前
    assert 上一 and re.search(r"没有|还没|无", 上一[0]), "空图上该答还没有完成的节点：%s" % 上一


def check_下一句是领域图里最早的那个节点(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 出一版 %s" % (前缀, 节点)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


def check_时限原样附上(workspace, reply):
    assert 时限 in reply, "「%s」在领域图上带时限句，往下的路里该原样附上：\n%s" % (节点, reply)
