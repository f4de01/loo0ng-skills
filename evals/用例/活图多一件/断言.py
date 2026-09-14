"""路由用例「活图多一件」的断言：领域图从活图取，不是包内的出厂种子（ADR-0019、#92）。签名 (workspace: Path, reply: str)。"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序)
from 基线 import 文件 as 三份图文件  # noqa: E402  只读基线看的就是这三份，名字只有一处

活图独有 = "裁定确认职工债权的申请"      # 只在活图上；出厂种子与工作区的三份图文件里都没有
活图独有的时限 = "自职工债权表公示之日起 15 日内提请法院裁定确认（活图，律师补）"
上一完成 = "裁定补充确认债权的申请"
出厂种子那条路会答的 = "管理人承诺书及团队人员"  # 读种子则问 3 落空、掉到问 4，领域图顺序最早的就是它
包内种子 = pathlib.Path("skills") / "domain" / "assets"


def 领域目录(workspace) -> pathlib.Path:
    """工作区 AGENTS.md 「领域目录」那一行：路由取领域图路径的唯一一步（ask-loo0ng/SKILL.md）。"""
    文 = (pathlib.Path(workspace) / "AGENTS.md").read_text(encoding="utf-8")
    m = re.search(r"^-\s*领域目录：(.+)$", 文, re.M)
    assert m, "工作区 AGENTS.md 里没有「领域目录」那一行：\n%s" % 文
    return pathlib.Path(m.group(1).strip())


def check_种子摆对了(workspace, reply):
    """先证判据本身成立：那一件只在活图上，工作区的三份图文件里一个字都没有。

    不成立的话下面那条「答出了活图上那一件」就退化成「读了图视图」，测不出本票要测的东西。
    """
    路径 = 领域目录(workspace)
    assert 包内种子.as_posix() not in 路径.as_posix(), \
        "AGENTS.md 记的领域目录还指着包内的出厂种子，这条用例的判据不成立：%s" % 路径
    活图 = json.loads((路径 / "领域图.json").read_text(encoding="utf-8"))
    assert 活图独有 in json.dumps(活图, ensure_ascii=False), "活图里没有「%s」，种子回放坏了" % 活图独有
    for 名 in 三份图文件:
        文 = (pathlib.Path(workspace) / 名).read_text(encoding="utf-8")
        assert 活图独有 not in 文, \
            "「%s」出现在 %s 里，那模型光读它就能答对，这条用例测不出有没有打开活图" % (活图独有, 名)


def check_命中问3(workspace, reply):
    assert re.search(r"命中问\s*3", reply), \
        "没有待确认、案件图里也没有未生成的，最近动过的那一块在活图上还差一件，该命中问 3：\n%s" % reply


def check_下一句是活图上那一件(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 出一版 %s" % (前缀, 活图独有)
        assert 串 in reply, \
            "回复里没有可原样打的整串「%s」：领域图要从 AGENTS.md 指的活图取，不是包内的出厂种子（ADR-0019）：\n%s" % (串, reply)


def check_没掉到出厂种子那条路上(workspace, reply):
    尾 = reply[reply.rfind("下一句该打什么"):]
    assert 出厂种子那条路会答的 not in 尾, \
        "「%s」是读出厂种子（那个模块一件不缺、问 3 落空掉到问 4）才会答的，读活图不该答它：\n%s" % (出厂种子那条路会答的, 尾)


def check_时限原样附上(workspace, reply):
    s = 段(reply, "往下的路")
    assert 活图独有的时限 in s, \
        "「%s」在活图上带时限句，往下的路里该原样附上；这句话只住活图（#71 那条死顺序在活图上照样成立，ADR-0016）：\n%s" % (活图独有, s)


def check_上一完成是确认最晚的那个(workspace, reply):
    行 = [l for l in 段(reply, "三问").splitlines() if "上一完成" in l]
    assert 行, "「三问」里没有上一完成这一行：\n%s" % reply
    assert 上一完成 in 行[0], "两件都已确认，上一完成该是确认最晚的「%s」：%s" % (上一完成, 行[0])
