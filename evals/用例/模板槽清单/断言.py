"""模板槽清单用例的断言：回复里有清单认出的占位、模板与图一字不动、没出件、没往工作区乱写。签名 (workspace: Path, reply: str)。"""
import hashlib
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 基线 import 校验基线  # noqa: E402
from 桶 import skill目录  # noqa: E402

模板名 = "1-2.关于管理人印章备案的报告.docx"
原件 = skill目录("domain") / "assets" / "预设图" / "破产" / "模板" / 模板名
根上允许 = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "待归档", "材料", "参考", "文书"}


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def check_回复里有槽(workspace, reply):
    """按清单的编号（`p2#1`）报，或把占位原文照读，两种都算：正文只要求把清单读给律师，没规定哪一种。"""
    assert re.search(r"p\d+#\d+|XX年X月X日", reply), \
        "该按清单的编号（p2#1 之类）或占位原文把槽报给律师：\n%s" % reply
    assert re.search(r"公安局|启用时间|落款|裁定", reply), "回复该说清槽在哪句话里：\n%s" % reply
    assert re.search(r"1[5-9]\s*个|共\s*1[5-9]", reply) or reply.count("p2#") >= 5, \
        "模板 1-2 有 17 个槽，该数得出来、不是只挑一两处说：\n%s" % reply


def check_模板原件没动(workspace, reply):
    p = workspace / "参考" / "模板" / 模板名
    assert p.is_file(), "模板原件不见了"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == hashlib.sha256(原件.read_bytes()).hexdigest(), "打清单不该改模板"


def check_图没动(workspace, reply):
    校验基线(workspace)


def check_没出件也没乱写(workspace, reply):
    assert not list((workspace / "文书").rglob("*")), "问槽不是出一版，文书/ 下不该有东西"
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    多 = [n for n in names if n not in 根上允许]
    assert not 多, "工作区根多出了东西：%s" % 多
