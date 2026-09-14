"""逐节点回流·已有的断言：领域图里已经有这个节点，一个字不问、一个字不写。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 活图断言 as 助手  # noqa: E402

带入, 带入的id = 助手.带入, 助手.带入的id   # 领域图里那个 id，惰性带入时原样带过来


def check_确认落在除草上(workspace, reply):
    助手.校验确认落了(workspace, 带入)


def check_活图逐字不变(workspace, reply):
    """提示词里预先授权了「还没有就直接写」，所以这一条测的是缺失判定本身：
    按 id 的反向减法算出来它已经在领域图里，就一个字不写（问的次数靠这一条衰减到零）。"""
    助手.校验活图逐字不变(workspace, "这个节点领域图里已经有了，不该回流")


def check_案件图里除草仍沿用领域图的id(workspace, reply):
    节点 = 助手.案件节点(workspace, 带入)[1]
    assert 节点["id"] == 带入的id, \
        "「%s」是按领域图带入的，id 该是 %r，实际 %r（id 变了，反向减法就失效）" % (带入, 带入的id, 节点["id"])


def check_活图里除草还是原来那一个(workspace, reply):
    命中 = [n for _, n in 助手.节点们(助手.活图(workspace)) if n["标题"] == 带入]
    assert len(命中) == 1, "活图里「%s」该只有一条，实际 %d 条" % (带入, len(命中))
    assert 命中[0]["id"] == 带入的id, "活图里「%s」的 id 被动了：%r" % (带入, 命中[0]["id"])


# 「一个字不问」的另一半：不向律师要一句关于归属的话。只认「向律师要一句话」这个形状，
# 不禁「领域图」三个字：模型说一句「除草领域图里已经有了，不用回流」是对的，不该因此报红。
要一句话 = r"要不要.{0,8}(写|加|回流|收)|写进.{0,6}领域图吗|归哪|归属.{0,8}[?？]|要改.{0,10}(就)?说"


def check_没向律师要归属那一句(workspace, reply):
    命中 = re.search(要一句话, reply)
    assert not 命中, "领域图里已经有它，不该再问一次归属，回复里却有 %r：\n%s" % (命中.group(0), reply)


def check_回复给了下一句(workspace, reply):
    assert "doit" in reply or "新对话" in reply, "收尾第三段没说下一句该打什么：\n%s" % reply
