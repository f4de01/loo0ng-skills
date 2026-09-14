"""回流用例的断言：活图恰好多出去案件化后的那一个节点，案件图一字未动。签名 (workspace: Path, reply: str)。"""
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 活图断言 as 助手  # noqa: E402  活图在哪、回流之前长什么样，只从种子写下的那份基线里读
import 回放助手          # noqa: E402  包内出厂种子的路径只有一处，与种子的回放读同一个常量

模块 = "接管与调查"
已确认 = "乙公司甲年乙月丙日厂区接管现场情况说明"
已确认的核心 = "接管现场情况说明"  # 「乙公司」「甲年乙月丙日」必去，「厂区」去不去归模型判
已生成的核心 = "食堂承包合同解除请示"


def _domain(workspace):
    return 助手.活图(workspace)


def _case(workspace):
    return json.loads((workspace / "案件" / "图.json").read_text(encoding="utf-8"))


def _基线(workspace):
    return 助手.基线(workspace)


def _nodes(data):
    return [(m["标题"], n) for m, n in 助手.节点们(data)]


def _回流的节点(workspace):
    """活图里那条回流进来的节点：(所在模块标题, 节点)。去案件化后的标题由模型定，只按核心词认。"""
    hit = [(mod, n) for mod, n in _nodes(_domain(workspace)) if 已确认的核心 in n["标题"]]
    assert len(hit) == 1, "去案件化后的那个节点该恰好有一条，实际 %s" % [n["标题"] for _, n in hit]
    return hit[0]


def _case_node(workspace, title):
    for _, n in _nodes(_case(workspace)):
        if n["标题"] == title:
            return n
    raise AssertionError("案件图里找不到节点「%s」" % title)


def check_回显里有去案件化后的标题(workspace, reply):
    assert 已确认的核心 in reply, "回复里没提那个候选：\n%s" % reply[:400]
    # 去案件化后的标题多半是案件里那个标题的真子串，所以先把原标题的所有出现抠掉，剩下的文字里还得有它，
    # 才算清单真的标出了去案件化后的标题，而不是只把案件里的原标题读了一遍。
    title = _回流的节点(workspace)[1]["标题"]
    assert title in reply.replace(已确认, ""), \
        "清单里没标出去案件化后的标题「%s」：\n%s" % (title, reply[:400])


def check_活图恰好多出那一个节点(workspace, reply):
    data = _domain(workspace)
    基线 = _基线(workspace)
    assert len(_nodes(data)) == 基线["节点数"] + 1, \
        "活图该只多出一个节点（回流前 %d 个），实际 %d 个" % (基线["节点数"], len(_nodes(data)))
    assert len(data["模块"]) == 基线["模块数"], "模块「%s」已在领域图里，不该多出模块" % 模块
    mod, node = _回流的节点(workspace)
    assert mod == 模块, "该落在领域图已有的模块「%s」下，实际「%s」" % (模块, mod)
    assert "乙公司" not in node["标题"] and "甲年" not in node["标题"], \
        "标题没去案件化，当事人或日期还在：%r" % node["标题"]
    assert node["空白模板"] == "无", "案件里那个节点没有空白模板，实际 %r" % node["空白模板"]


def check_包内出厂种子一个字节没动(workspace, reply):
    """写的得是活图那一份（ADR-0020）：整个领域目录 22 件逐文件比，不是只比 领域图.json。

    期望值取基线里那份指纹：活图是 `home` 从种子整份拷出来的逐字副本，两边的相对路径与 sha256
    本来就该一模一样。「逐字副本」这个前提由 tests/domain/test_seeds.py 的
    test_活图是包内出厂种子的一份拷贝 钉着，home 哪天改成带改写的拷贝，那条先红。
    """
    现在, 当初 = 助手.指纹(回放助手.出厂种子), _基线(workspace)["指纹"]
    变了 = ["%s 没了" % k for k in 当初 if k not in 现在]
    变了 += ["%s 多出来" % k for k in 现在 if k not in 当初]
    变了 += ["%s 的字节变了" % k for k in 当初 if k in 现在 and 现在[k] != 当初[k]]
    assert not 变了, ("包内出厂种子被动了：回流只写活图，一次 eval 也不该动到 skills/ 下的东西"
                      "（ADR-0015、ADR-0020）：%s" % "、".join(变了))


def check_新节点排在那个模块的末尾(workspace, reply):
    module = next(m for m in _domain(workspace)["模块"] if m["标题"] == 模块)
    assert 已确认的核心 in module["节点"][-1]["标题"], \
        "回流的节点该追加在模块末尾，不该插进领域图原有的顺序里：%s" % [n["标题"] for n in module["节点"]]


def check_id与案件图一致且无条目(workspace, reply):
    node = _回流的节点(workspace)[1]
    assert node["id"] == _case_node(workspace, 已确认)["id"], \
        "回流保留案件里的原 id（ADR-0012），实际活图里是 %r" % node["id"]
    assert node["条目"] == [], "领域图没有条目（ADR-0012），实际 %s" % node["条目"]


def check_只生成没拍板的那个没回流(workspace, reply):
    titles = [n["标题"] for _, n in _nodes(_domain(workspace))]
    带过去的 = [t for t in titles if 已生成的核心 in t]
    assert not 带过去的, "只生成没拍板的节点不是候选（判据 a，ADR-0012），却进了活图：%s" % 带过去的


def check_活图仍是一张合法的领域图(workspace, reply):
    data = _domain(workspace)
    assert set(data) == {"格式版本", "领域", "模块"}, "活图顶层多了键：%s" % sorted(data)
    assert data["领域"] == "破产", "领域名被动了：%r" % data["领域"]
    ids = [n["id"] for _, n in _nodes(data)] + [m["id"] for m in data["模块"]]
    assert len(ids) == len(set(ids)), "活图里 id 重复了"


def check_案件图字节不变(workspace, reply):
    digest = hashlib.sha256((workspace / "案件" / "图.json").read_bytes()).hexdigest()
    assert digest == _基线(workspace)["案件图sha256"], \
        "回流只读案件图，案件图不该有任何改动（ADR-0012）"


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。

    #105 实测 Codex 也会把 uv 的缓存落成不带点的 `uv-cache`，所以 `uv-` 开头的一并忽略：
    它是 harness 自备解释器留下的，不是 skill 的产物。七份同名小函数逐字相同，改一处就一起改。
    """
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def check_雏形文件没落进工作区(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["案件"], \
        "工作区里多出了文件（活图在工作区外，雏形文件该写在临时目录）：%s" % names
