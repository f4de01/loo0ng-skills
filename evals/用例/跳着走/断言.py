"""路由用例「跳着走」的断言：命中问 3、上一完成是确认最晚的、下一句照前方给（不因律师跳着走重排）。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

前方第一 = "管理人工作计划"
上一完成 = "债权表"
债权那一块的 = ("债权申报与审核流程规则", "已知债权人债权申报通知", "债权申报登记册", "职工债权表", "债权核查报告")


def check_命中问3(workspace, reply):
    assert re.search(r"命中问\s*3", reply), "没有待确认的、前方还有节点，该命中问 3：\n%s" % reply


def check_上一完成是确认最晚的(workspace, reply):
    s = 段(reply, "三问")
    上一 = [l for l in s.splitlines() if "上一完成" in l]
    assert 上一 and 上一完成 in 上一[0], "上一完成该是确认最晚的「%s」：%s" % (上一完成, 上一)


def check_下一句照前方给(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 出一版 %s" % (前缀, 前方第一)
        assert 串 in reply, "前方按图序从第一个模块算，下一句该是「%s」：\n%s" % (串, reply)
    尾 = 段(reply, "下一句该打什么")
    for t in 债权那一块的:
        assert t not in 尾, "路由照前方给、不自己重排，最后一段不该跳到「%s」：\n%s" % (t, 尾)
