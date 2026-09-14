"""回流用例共用的读法：活图在哪、回流之前长什么样、跑完变了什么（#91 验收，ADR-0019）。

活图不在工作区里（它住 `<活图家>/领域/<领域名>/`，跑器每次运行另建一个活图家经 LOO0NG_HOME
交给 harness），断言的签名又只有 (workspace, reply)，所以路径与回流前的指纹由种子写进工作区根的
点开头文件 `.活图基线.json`，这里从那份基线里读。

前半段（`基线名`、`基线`、`活图目录`、`活图`、`指纹`、`节点们`）不认领域，律师侧那四条逐节点用例
与开发侧用例「回流」都读它；带「菜园」名字的常量与后面几条校验只供逐节点那四条。

「逐字不变」比的是活图目录里每个文件的 sha256，不是领域图的内容：模型若只是多跑了一次写入、
写回同样的内容，字节仍会变（引擎每次落盘都重排），那也是一次写入，该红。
"""
import hashlib
import json
import pathlib

基线名 = ".活图基线.json"
领域名 = "菜园"          # 合成小领域，evals/领域/菜园/ 是它的「出厂种子」

# 种子「逐节点回流」摆出来的两个已生成未确认的节点。种子的回放与 tests/domain/test_seeds.py
# 也从这里读：一份名字改了，回放、四条用例的断言与单测一起跟着改，不会漏掉哪一处。
自加 = "乙家甲年乙月丙日南墙菜畦补种记录"   # 领域图里没有它（律师自加，id 由引擎生成）
自加所在模块 = "养护"                       # 归属提案的默认模块就是它
自加的核心词 = "补种"                       # 去案件化之后必留的那两个字，标题怎么改归模型判
带入 = "除草"                               # 领域图带入的，领域图里已经有
带入的id = "n-chucao"                       # 就是领域图里那个 id：反向减法靠它认出「已经有」


def 基线(workspace) -> dict:
    p = pathlib.Path(workspace) / 基线名
    assert p.is_file(), "种子没写下 %s，这几条断言无从比对" % 基线名
    return json.loads(p.read_text(encoding="utf-8"))


def 活图目录(workspace) -> pathlib.Path:
    d = pathlib.Path(基线(workspace)["活图"])
    assert d.is_dir(), "基线里记的活图目录不在了：%s" % d
    return d


def 活图(workspace) -> dict:
    return json.loads((活图目录(workspace) / "领域图.json").read_text(encoding="utf-8"))


def 指纹(root: pathlib.Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def 校验活图逐字不变(workspace, 为什么: str) -> None:
    root = 活图目录(workspace)
    现在, 当初 = 指纹(root), 基线(workspace)["指纹"]
    变了 = ["%s 没了" % k for k in 当初 if k not in 现在]
    变了 += ["%s 多出来" % k for k in 现在 if k not in 当初]
    变了 += ["%s 的字节变了" % k for k in 当初 if k in 现在 and 现在[k] != 当初[k]]
    assert not 变了, "%s，活图该一个字节都不变：%s" % (为什么, "、".join(变了))


def 节点们(data):
    return [(m, n) for m in data["模块"] for n in m["节点"]]


def 案件图(workspace):
    return json.loads((pathlib.Path(workspace) / "图.json").read_text(encoding="utf-8"))


def 案件节点(workspace, 标题):
    for m, n in 节点们(案件图(workspace)):
        if n["标题"] == 标题:
            return m, n
    raise AssertionError("案件图里找不到节点「%s」：%s" %
                         (标题, [n["标题"] for _, n in 节点们(案件图(workspace))]))


def 校验确认落了(workspace, 标题) -> None:
    """这几条用例先得是一次正常的拍板：末条是确认、来源律师、原话不是模型自己的话。"""
    条目 = 案件节点(workspace, 标题)[1]["条目"]
    动作 = [e["动作"] for e in 条目]
    assert 动作 == ["生成", "确认"], "节点「%s」该是种子那条生成加这次的确认，实际 %s" % (标题, 动作)
    assert 条目[-1]["来源"] == "律师", "确认的来源恒为律师，实际 %r" % 条目[-1]["来源"]
    assert 条目[-1].get("原话"), "确认条目没有原话（留痕规则 a）"


def 校验回流进活图的那个节点(workspace, 核心词, 期望模块, 期望标题=None):
    """活图里那条新写进去的节点：(所在模块标题, 节点)。标题由模型去案件化，只按核心词认。

    「不给时限句」不在这里查：它是本票自己的一条验收项，各用例有一条同名断言单管，
    混进这个共用的读法里，别的断言会跟着报同一条消息，报红时看不出真正错的是哪一样。
    """
    hit = [(m["标题"], n) for m, n in 节点们(活图(workspace)) if 核心词 in n["标题"]]
    assert len(hit) == 1, "带「%s」的节点该恰好有一条，实际 %s" % (核心词, [n["标题"] for _, n in hit])
    模块, 节点 = hit[0]
    assert 模块 == 期望模块, "该落在模块「%s」下，实际「%s」" % (期望模块, 模块)
    if 期望标题 is not None:
        assert 节点["标题"] == 期望标题, "标题该按律师说的写成「%s」，实际 %r" % (期望标题, 节点["标题"])
    assert 节点["条目"] == [], "领域图没有条目，实际 %s" % 节点["条目"]
    return 模块, 节点


def 校验活图只多出那一个(workspace, 多几个模块=0):
    base = 基线(workspace)
    data = 活图(workspace)
    assert len(节点们(data)) == base["节点数"] + 1, \
        "活图该只多出一个节点（回流前 %d 个），实际 %d 个" % (base["节点数"], len(节点们(data)))
    assert len(data["模块"]) == base["模块数"] + 多几个模块, \
        "活图的模块数该是 %d，实际 %d" % (base["模块数"] + 多几个模块, len(data["模块"]))
    assert set(data) == {"格式版本", "领域", "模块"}, "活图顶层多了键：%s" % sorted(data)
    assert data["领域"] == 领域名, "领域名被动了：%r" % data["领域"]
    ids = [n["id"] for _, n in 节点们(data)] + [m["id"] for m in data["模块"]]
    assert len(ids) == len(set(ids)), "活图里 id 重复了"
