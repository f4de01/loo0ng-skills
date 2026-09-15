"""换节点被拒用例的断言：图一条条目没有、文书/ 下一件文件没有、回复既说了缺模板又让第二个节点开新对话。

签名 (workspace: Path, reply: str)。
"""
import json
import re

根上允许 = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "待归档", "材料", "参考", "文书"}


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def check_图一字不动(workspace, reply):
    data = json.loads((workspace / "图.json").read_text(encoding="utf-8"))
    titles = {m["标题"]: [n["标题"] for n in m["节点"]] for m in data["模块"]}
    assert titles == {"整地": ["松土", "施底肥"], "播种": ["选种", "下种"], "养护": ["浇水", "除草", "搭架"],
                      "收获": ["采摘", "记账"]}, "图的构成被动了：%s" % titles
    assert all(n["条目"] == [] for m in data["模块"] for n in m["节点"]), "没有模板就不出件，图上不该有条目"


def check_文书下一件都没有(workspace, reply):
    有 = sorted(p.relative_to(workspace).as_posix() for p in (workspace / "文书").rglob("*") if p.is_file())
    assert 有 == [], "没有模板本版出不了文书，文书/ 下却有：%s" % 有


def check_说了缺模板(workspace, reply):
    assert re.search(r"模板", reply), "回复该说清缺的是空白模板、从哪来：\n%s" % reply
    assert "松土" in reply, "回复该点名是「松土」缺模板：\n%s" % reply


def check_第二个节点停下开新对话(workspace, reply):
    assert "除草" in reply, "回复该单独给「除草」一段：\n%s" % reply
    assert re.search(r"新对话|新开对话|另开|再开", reply), "第二个节点该停下、让律师开新对话：\n%s" % reply
    assert re.search(r"doit 出一版 ?除草", reply), "该给出新对话的第一句「doit 出一版 除草」：\n%s" % reply


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    多 = [n for n in names if n not in 根上允许]
    assert not 多, "工作区根多出了东西：%s" % 多
