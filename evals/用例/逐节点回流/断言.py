"""逐节点回流用例的断言：确认之后活图恰好多出去案件化后的那一个节点。签名 (workspace: Path, reply: str)。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 活图断言 as 助手  # noqa: E402

自加, 核心 = 助手.自加, 助手.自加的核心词   # 「乙家」「甲年乙月丙日」必去，「南墙菜畦」去不去归模型判
默认模块 = 助手.自加所在模块                # 它在案件图里所在的那个模块，ADR-0019 的默认值


def check_确认落在补种那个节点上(workspace, reply):
    助手.校验确认落了(workspace, 自加)


def check_回显里有去案件化后的标题(workspace, reply):
    assert 核心 in reply, "回复里没提那个节点：\n%s" % reply[:400]
    # 去案件化后的标题多半是案件里那个标题的真子串，所以先把原标题的所有出现抠掉，剩下的文字里还得有它，
    # 才算真的回显过归属提案，而不是只把案件里的原标题读了一遍。
    标题 = 助手.校验回流进活图的那个节点(workspace, 核心, 默认模块)[1]["标题"]
    assert 标题 in reply.replace(自加, ""), \
        "回复里没回显归属提案里那个去案件化后的标题「%s」：\n%s" % (标题, reply[:400])


def check_活图恰好多出那一个节点(workspace, reply):
    助手.校验活图只多出那一个(workspace)
    节点 = 助手.校验回流进活图的那个节点(workspace, 核心, 默认模块)[1]
    assert "乙家" not in 节点["标题"] and "甲年" not in 节点["标题"], \
        "标题没去案件化，当事人或日期还在：%r" % 节点["标题"]
    assert 节点["空白模板"] == "无", "案件里那个节点没有空白模板，实际 %r" % 节点["空白模板"]


def check_模块默认继承案件图里那个(workspace, reply):
    模块 = 助手.校验回流进活图的那个节点(workspace, 核心, 默认模块)[0]
    assert 模块 == 默认模块, "律师没改模块时该继承案件图里的「%s」，实际「%s」" % (默认模块, 模块)


def check_id与案件图一致(workspace, reply):
    节点 = 助手.校验回流进活图的那个节点(workspace, 核心, 默认模块)[1]
    案件 = 助手.案件节点(workspace, 自加)[1]
    assert 节点["id"] == 案件["id"], \
        "回流保留案件里的原 id，否则本案的前方立刻多出一个与自己重复的节点，实际活图里是 %r" % 节点["id"]


def check_没给时限句(workspace, reply):
    节点 = 助手.校验回流进活图的那个节点(workspace, 核心, 默认模块)[1]
    assert "时限" not in 节点, \
        "律师侧新增的节点不给时限句（ADR-0019），实际带了 %r" % 节点.get("时限")


def check_案件图里那个节点没被改(workspace, reply):
    """回流只往领域图写：案件图里那个节点的标题、id、空白模板一个字不动（标题由 案件节点 按名字找到即证）。"""
    模块, 节点 = 助手.案件节点(workspace, 自加)
    assert 模块["标题"] == 默认模块, "案件图里那个节点被挪走了：现在在「%s」下" % 模块["标题"]
    assert 节点["空白模板"] == "无", "案件图里那个节点的空白模板被动了：%r" % 节点["空白模板"]
    assert 节点["id"] == 助手.校验回流进活图的那个节点(workspace, 核心, 默认模块)[1]["id"],         "案件图里那个节点的 id 被改了：回流只往领域图写，案件图一个字不动"


def check_回复给了下一句(workspace, reply):
    assert "doit" in reply or "新对话" in reply, "收尾第三段没说下一句该打什么：\n%s" % reply
