"""测试工作区构造器：在临时目录里用图引擎自己起一个案件工作区（#12 交付，供别的测试目录 import）。

为什么不从 `evals/种子/` 拷：种子是路由用例的既有状态，形状跟着 0.1.0 的目录走，改一次工作流
就要改一轮种子，而单测要的只是「一个形状对的空工作区」。这里从零造，目录形状与预设图都由这份
文件说了算，改形状只改这里。

怎么用（别的测试目录里两行）：

    sys.path.insert(0, str(REPO / "tests" / "共用"))
    import 工作区 as 工

    ws = 工.起工作区(self.tmp)                       # 空图
    ws = 工.起工作区(self.tmp, 预设图=工.造预设图(d, 工.菜园))  # 整份拷入

造出来的东西一律是合成的：领域是「菜园」，当事人写甲乙丙，不含隐私检查器五类正则能命中的值，
也不含任何破产语义（ADR-0015：引擎不认领域）。
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
引擎脚本 = REPO / "skills" / "in-progress" / "graph" / "scripts" / "graph.py"

_spec = importlib.util.spec_from_file_location("loo0ng_graph_for_tests", 引擎脚本)
引擎 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(引擎)

# 工作区的目录形状（ADR-0023 第 2 节）。起手建这几格，起手之后它们都是空的。
目录 = ("待归档", "材料", "参考/模板", "参考/指南", "文书")

# 合成小领域「菜园」：四个模块、九个节点，两个带时限、两个带空白模板。
# 形状够用就行：有排序、有跨模块、有带模板的与不带的，够断前方、目录名、另存与模块级不适用。
菜园 = [
    ("整地", [("松土", None, None),
              ("施底肥", "施肥记录.docx", "自松土完成之日起 3 日内（手册，示例）")]),
    ("播种", [("选种", None, None),
              ("下种", "播种登记.docx", None)]),
    ("养护", [("浇水", None, None),
              ("除草", None, None),
              ("搭架", None, None)]),
    ("收获", [("采摘", None, None),
              ("记账", None, "自采摘结束之日起 7 日内（手册，示例）")]),
]


class 结果:
    """一次引擎调用的退出码与两股输出。测试直接断 code 与 out/err 里的字。"""

    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "结果(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


def 跑引擎(*argv, **kw):
    """在本进程里调 graph.main(argv)，拿回退出码与输出。argv 里的 Path 自动转字符串。"""
    args = [str(a) for a in argv]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = 引擎.main(args)
        except SystemExit as e:  # argparse 的用法错误
            code = e.code
    r = 结果(code, out.getvalue(), err.getvalue())
    if kw.get("须过", False) and r.code != 0:
        raise AssertionError("引擎该过却拒了：%r\n%s" % (args, r))
    return r


def 造预设图(目标目录, 模块=菜园, 名=None):
    """用引擎自己（--kind preset）造一份预设图目录，回它的路径。

    一律走 CLI 而不是手写 JSON：预设图的形状只有引擎说了算，引擎一改这里立刻跟着红，
    不会出现「测试里的预设图合法、真的预设图不合法」那种两份真相。
    """
    目标目录 = pathlib.Path(目标目录)
    if 名:
        目标目录 = 目标目录 / 名
    目标目录.mkdir(parents=True, exist_ok=True)
    (目标目录 / "模板").mkdir(exist_ok=True)
    图 = 目标目录 / 引擎.PRESET_FILENAME
    基 = ["--graph", 图, "--kind", "preset"]
    跑引擎(*基, "init", "--empty", 须过=True)
    for i, (模块标题, 节点们) in enumerate(模块):
        跑引擎(*基, "add-module", "--title", 模块标题, "--id", "m-%d" % (i + 1), 须过=True)
        for j, (节点标题, 模板, 时限) in enumerate(节点们):
            参数 = ["add-node", "--module", 模块标题, "--title", 节点标题, "--id", "n-%d-%d" % (i + 1, j + 1)]
            if 模板:
                参数 += ["--template", 模板]
                写空白模板(目标目录 / "模板" / 模板)
            if 时限:
                参数 += ["--time-limit", 时限]
            跑引擎(*基, *参数, 须过=True)
    return 目标目录


class 工作区:
    """一个起好手的案件工作区。属性都是绝对路径，方法是测试里常用的那几个动作。"""

    def __init__(self, 根: pathlib.Path):
        self.根 = pathlib.Path(根)
        self.图 = self.根 / 引擎.DEFAULT_GRAPH
        self.视图md = self.根 / 引擎.VIEW_MD
        self.视图json = self.根 / 引擎.VIEW_JSON
        self.待归档 = self.根 / "待归档"
        self.材料 = self.根 / "材料"
        self.模板 = self.根 / "参考" / "模板"
        self.指南 = self.根 / "参考" / "指南"
        self.文书 = self.根 / "文书"

    def 调(self, *argv, **kw):
        return 跑引擎("--graph", self.图, *argv, **kw)

    def 读图(self):
        return json.loads(self.图.read_text(encoding="utf-8"))

    def 读视图(self):
        return json.loads(self.视图json.read_text(encoding="utf-8"))

    def 读视图文(self):
        return self.视图md.read_text(encoding="utf-8")

    def 节点(self, 标题, 图=None):
        for m in (图 or self.读图())["模块"]:
            for n in m["节点"]:
                if n["标题"] == 标题 or n["id"] == 标题:
                    return n
        raise AssertionError("图里没有节点 %s" % 标题)

    def 模块(self, 标题, 图=None):
        for m in (图 or self.读图())["模块"]:
            if m["标题"] == 标题 or m["id"] == 标题:
                return m
        raise AssertionError("图里没有模块 %s" % 标题)

    def 节点标题(self, 模块标题, 图=None):
        return [n["标题"] for n in self.模块(模块标题, 图)["节点"]]

    def 模块标题(self, 图=None):
        return [m["标题"] for m in (图 or self.读图())["模块"]]

    def 视图节点(self, 标题, 视图=None):
        for m in (视图 or self.读视图())["模块"]:
            for n in m["节点"]:
                if n["标题"] == 标题:
                    return n
        raise AssertionError("视图里没有节点 %s" % 标题)

    def 文书相对路径(self, 模块标题, 节点标题):
        """文书/<模块目录名>/<节点目录名>/<节点目录名>.docx，转义规则取引擎那一份。"""
        m, n = 引擎.dirname_of(模块标题), 引擎.dirname_of(节点标题)
        return "文书/%s/%s/%s.docx" % (m, n, n)

    def 出一版(self, 模块标题, 节点标题, 高亮=False, 落盘=True):
        """造一份文书与审查报告，再调引擎追加生成条目；回那条文书的相对路径。"""
        相对 = self.文书相对路径(模块标题, 节点标题)
        审查 = 相对[: -len(".docx")] + "-审查报告.md"
        if 落盘:
            写文书(self.根 / 相对, ["甲方与乙方就本节点达成如下记载。"], 高亮=高亮)
            (self.根 / 审查).write_text("# 审查报告\n\n合成件，供测试用。\n", encoding="utf-8")
        self.调("generate", "--node", 节点标题, "--doc", 相对, "--review", 审查, 须过=True)
        return 相对


def 起工作区(根, 预设图=None) -> 工作区:
    """建目录形状，再用引擎起图：给了预设图目录就整份拷入，不给就是空图。"""
    ws = 工作区(根)
    ws.根.mkdir(parents=True, exist_ok=True)
    for 格 in 目录:
        (ws.根 / 格).mkdir(parents=True, exist_ok=True)
    if 预设图 is None:
        ws.调("init", "--empty", 须过=True)
    else:
        ws.调("init", "--preset", 预设图, 须过=True)
        for 模板 in sorted((pathlib.Path(预设图) / "模板").glob("*")):
            (ws.模板 / 模板.name).write_bytes(模板.read_bytes())
    return ws


# ---------------------------------------------------------------- 合成 docx

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/></Relationships>'
)
_DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
)
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _段(文字, 高亮):
    属性 = '<w:rPr><w:highlight w:val="yellow"/></w:rPr>' if 高亮 else ""
    return "<w:p><w:r>%s<w:t xml:space=\"preserve\">%s</w:t></w:r></w:p>" % (属性, 文字)


def 写文书(路径, 段落, 高亮=False, 高亮段=()):
    """写一份能被 python-docx 打开的最小 docx。

    高亮=True 把每一段都标黄；高亮段 给段落下标（从 0 起）只标其中几段。两者都不给就是一份
    没有任何高亮的文书，引擎的「高亮已清」那一列会算成 已清。
    """
    路径 = pathlib.Path(路径)
    路径.parent.mkdir(parents=True, exist_ok=True)
    段们 = "".join(_段(t, 高亮 or i in set(高亮段)) for i, t in enumerate(段落))
    文档 = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="%s"><w:body>%s</w:body></w:document>' % (_W, 段们))
    with zipfile.ZipFile(str(路径), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/document.xml", 文档)
    return 路径


def 写空白模板(路径):
    """预设图 模板/ 下的一件空白模板：一段提示句加一处模板自带的黄。"""
    return 写文书(路径, ["本表由甲方填写。", "（注：不适用的栏目划去。）"], 高亮段=(1,))
