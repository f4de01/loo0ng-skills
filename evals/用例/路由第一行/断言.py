"""路由用例「路由第一行」的断言：第一行是待拍板行，点黄色已清的那份、不点没清的、带确认那一串。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 第一行  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

已清的 = "管理人印章备案报告"
未清的 = "管理人银行账户备案报告"


def check_第一行点名并给整串(workspace, reply):
    行 = 第一行(reply)
    assert re.match(r"[*#\s]*待拍板", 行), "第一个非空行该以「待拍板」起头，实际：%r" % 行
    assert 已清的 in 行, "黄色已清、还没确认的「%s」该在第一行点名：%r" % (已清的, 行)
    assert re.search(r"[/$]doit 确认 ?%s" % 已清的, 行), "第一行该带「/doit 确认 %s」那一串：%r" % (已清的, 行)
    assert 未清的 not in 行, "「%s」黄色没清，不算待拍板，不该出现在第一行：%r" % (未清的, 行)
    assert "已清" in 行 or "黄色" in 行, "第一行该说明是黄色已清、还没确认：%r" % 行


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "有一份黄色已清、等确认，该命中问 1：\n%s" % reply
