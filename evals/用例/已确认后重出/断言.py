"""路由用例「已确认后重出」的断言：重出的那份回到待确认、上一完成退回另一份、下一句是确认重出的那版。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

重出的 = "管理人承诺书及团队人员"
仍已确认的 = "管理人印章备案报告"


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "重出的那份黄色已清、等确认，该命中问 1：\n%s" % reply


def check_当前节点是重出的那份(workspace, reply):
    s = 段(reply, "三问")
    当前 = [l for l in s.splitlines() if "当前节点" in l]
    assert 当前 and 重出的 in 当前[0], "当前节点该是重出后等确认的「%s」：%s" % (重出的, 当前)


def check_上一完成退回印章备案(workspace, reply):
    s = 段(reply, "三问")
    上一 = [l for l in s.splitlines() if "上一完成" in l]
    assert 上一 and 仍已确认的 in 上一[0], "重出过的不算完成，上一完成该退回「%s」：%s" % (仍已确认的, 上一)
    assert 重出的 not in 上一[0], "「%s」重出后已不是已确认，不该算上一完成：%s" % (重出的, 上一)


def check_下一句是确认重出的那版(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 确认 %s" % (前缀, 重出的)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


# `ask-loo0ng` 正文「逐行逐段的规矩」第 5 条列出的四对相邻入口，各记成这一对两边的关键词。
正文列的四对 = (
    ("自己填", "重出"),
    ("确认", "不适用"),
    ("节点不适用", "模块不适用"),
    ("出一版", "登记"),
)


def check_分界线列的是正文那几对(workspace, reply):
    """分界线列的是正文第 5 条那四对里的某一对，不钉死哪一对。

    放宽过一次（#84）：原来只认带「重出」或「出一版」的那一对，Codex 侧稳定选「确认还是不适用」
    而红。本场景（重出的那份黄色已清、就等确认）里「确认还是不适用」同样与这一步相邻，正文把选
    哪一对明写着留给模型，钉死一对守的是用例作者的期待而不是正文。「认没认出自己在重出」由
    check_当前节点是重出的那份、check_上一完成退回印章备案、check_下一句是确认重出的那版三条验，
    不靠这一条；想收紧回去之前，先确认那三条真的兜不住。
    """
    s = 段(reply, "相近入口分界线")
    行 = [l for l in s.splitlines() if "还是" in l]
    assert any(左 in l and 右 in l for l in 行 for 左, 右 in 正文列的四对), \
        "相近入口分界线该列正文第 5 条那四对相邻入口里的某一对：\n%s" % s
