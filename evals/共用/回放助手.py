"""种子共用的回放动作（#20 重定，ADR-0023）。

每个种子都是「用真的起手 CLI 起一个案件工作区，再逐条调引擎与归档摆出一个状态」，只有那几条命令
不同；重复的部分收在这里，种子的 `回放.py` 只剩它自己那几步，读起来就是那个状态本身。
起手、写图、归档都走真的 CLI（skill "setup-case"、skill "graph"、skill "filing"），
哪一件一改，用这些种子的用例立刻红。

预设图两处两归属（ADR-0023）：出厂件在包内 `assets/预设图/破产/`，按名解析、原位读；个人预设图
住「家」（环境变量 LOO0NG_HOME 下的 预设图/），跑器每次运行建一个临时的家交给两侧 harness，
没设这个变量时（--materialize、脚本层单测）回放把家落在工作区里的 `.预设图家/`，永远不碰
律师真的 ~/.loo0ng/。合成小领域「菜园」就是这样一份个人预设图，由本模块用引擎现造。

文书都是合成的最小 docx（几句话、可带或不带高亮），审查报告按四段写；当事人与法院一律写
甲乙丙，不含隐私检查器五类正则能命中的值。跑得动 python 3.9（#61）。
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import 桶  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
# 住哪个桶不写死，按 skill 名当场解析（evals/共用/桶.py）：搬桶时这里一个字都不用改。
SETUP = 桶.脚本("setup-case", "setup.py")
ENGINE = 桶.脚本("graph", "graph.py")
PRESET = 桶.脚本("domain", "preset.py")
ARCHIVE = 桶.脚本("filing", "archive.py")
FILL = 桶.脚本("to-docx", "fill.py")
出厂预设图 = 桶.skill目录("domain") / "assets" / "预设图"
官方模板 = 出厂预设图 / "破产" / "模板"

HOME_ENV = "LOO0NG_HOME"     # 个人预设图的家，与 preset.py、跑器同一个名字
WS_HOME = ".预设图家"         # 没设 HOME_ENV 时家落在工作区里的这个目录（点开头：不算「往工作区乱写」）
PRESETS_DIRNAME = "预设图"    # <家>/预设图/<名>/

破产 = "破产"                 # 出厂那一份的名
菜园 = "菜园"                 # 合成小领域，个人预设图

# 合成小领域「菜园」：四个模块、九个节点，两个带时限、两个挂空白模板（与 tests/共用/工作区.py 同一张表）。
# 不含任何破产语义：证明引擎、起手、路由不认领域内容（ADR-0015「领域两用」）。
菜园构成 = [
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


# ---------------------------------------------------------------- 子进程

def run(ws, *args, env=None):
    r = subprocess.run([sys.executable, *[str(a) for a in args]], cwd=str(ws),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
        raise SystemExit(r.returncode)
    return r.stdout


_上次写图 = [0.0]


def 隔开一秒():
    """两次写图之间等到整秒跳一格：条目时间只到秒，同一秒里落两条就分不出先后，
    「上一完成 = 确认最晚的」这条断言会变成掷硬币（#33 的用例「跳着走」上真的撞上过）。"""
    while int(time.time()) <= int(_上次写图[0]):
        time.sleep(0.05)


def 引擎(ws, *args):
    """在工作区里调图引擎：--graph 默认当前目录的 图.json，每次写完重算两份视图。"""
    隔开一秒()
    out = run(ws, ENGINE, *args)
    _上次写图[0] = time.time()
    return out


# ---------------------------------------------------------------- 家与预设图

def 家(ws) -> pathlib.Path:
    """个人预设图的家：取环境变量 HOME_ENV；没设就落在工作区里的 .预设图家/，并把变量设上，
    往后本进程起的起手与 preset.py 子进程都吃它。回的是 <家> 本身（预设图在它的 预设图/ 下）。"""
    if not os.environ.get(HOME_ENV, "").strip():
        os.environ[HOME_ENV] = str(pathlib.Path(ws) / WS_HOME)
    home = pathlib.Path(os.environ[HOME_ENV])
    (home / PRESETS_DIRNAME).mkdir(parents=True, exist_ok=True)
    return home


def 个人预设图目录(ws, 名) -> pathlib.Path:
    return 家(ws) / PRESETS_DIRNAME / 名


def 造菜园(ws, 名=菜园, 构成=菜园构成) -> pathlib.Path:
    """在家里用引擎（--kind preset）造一份个人预设图，回它的目录。形状只有引擎说了算：手写 JSON 会出现
    「种子里的预设图合法、真的预设图不合法」两份真相。挂着模板的节点在 模板/ 下各放一件最小 docx。"""
    目录 = 个人预设图目录(ws, 名)
    if (目录 / "预设图.json").is_file():
        return 目录
    (目录 / "模板").mkdir(parents=True, exist_ok=True)
    基 = [ENGINE, "--graph", 目录 / "预设图.json", "--kind", "preset"]
    run(ws, *基, "init", "--empty")
    for i, (模块标题, 节点们) in enumerate(构成):
        run(ws, *基, "add-module", "--title", 模块标题, "--id", "m-%d" % (i + 1))
        for j, (节点标题, 模板, 时限) in enumerate(节点们):
            参数 = ["add-node", "--module", 模块标题, "--title", 节点标题, "--id", "n-%d-%d" % (i + 1, j + 1)]
            if 模板:
                参数 += ["--template", 模板]
                写文书(目录 / "模板" / 模板, ["本表由甲方填写。", "（注：不适用的栏目划去。）"], 高亮段=(1,))
            if 时限:
                参数 += ["--time-limit", 时限]
            run(ws, *基, *参数)
    return 目录


# ---------------------------------------------------------------- 起手与状态

def 起手(ws, 预设图=None, 归属="出厂"):
    """走真的起手 CLI：不给预设图就是空图；给了就 --preset <名> --owner <归属> 整份拷入。
    个人预设图要先在家里造好（造菜园）。"""
    参数 = [SETUP, "init", "--workspace", ws]
    if 预设图:
        参数 += ["--preset", 预设图, "--owner", 归属]
    return run(ws, *参数)


def 视图(ws) -> dict:
    return json.loads((pathlib.Path(ws) / "图视图.json").read_text(encoding="utf-8"))


def 目录名(ws, 节点标题):
    """(模块目录名, 节点目录名)：取引擎在视图里算好的那一份，不自己转义（ADR-0023）。"""
    for m in 视图(ws)["模块"]:
        for n in m["节点"]:
            if n["标题"] == 节点标题:
                return m["目录名"], n["目录名"]
    raise SystemExit("图里没有节点「%s」" % 节点标题)


def 文书路径(ws, 节点标题):
    """(文书相对路径, 审查报告相对路径)：文书/<模块>/<节点>/<节点>.docx 与同名 -审查报告.md。"""
    模块目录, 节点目录 = 目录名(ws, 节点标题)
    基 = "文书/%s/%s/%s" % (模块目录, 节点目录, 节点目录)
    return 基 + ".docx", 基 + "-审查报告.md"


def 审查报告(标题, 高亮=()):
    """四段固定的合成审查报告（skill "to-docx" 的 references/审查报告.md）。高亮给几处就记几处。"""
    清单 = ["高亮清单 %d 处" % len(高亮)] + ["p%d「%s」｜%s" % (i + 1, 原文, 整段) for i, (原文, 整段) in enumerate(高亮)]
    return ("# %s 审查报告\n\n## 生成依据\n\n- 合成种子，无真实材料\n"
            "- 出件环境：合成种子，没有施加\n\n## 高亮清单\n\n%s\n\n## 施加原话\n\n"
            "合成种子，没有施加\n\n## 时限\n\n无明示时限\n" % (标题, "\n".join(清单)))


def 出一版(ws, 节点标题, 高亮=False):
    """写一份合成文书与审查报告，再经引擎追加生成条目；回文书的相对路径。
    高亮=True 让文书里带一处黄（引擎的「高亮」列算 未清），False 就是律师在 Word 里都填完了的样子（已清）。"""
    ws = pathlib.Path(ws)
    文书, 报告 = 文书路径(ws, 节点标题)
    段落 = ["%s：本件为合成稿，只求形状对。" % 节点标题, "甲公司与乙公司就本节点达成如下记载，由丙经办。"]
    写文书(ws / 文书, 段落, 高亮段=(1,) if 高亮 else ())
    (ws / 报告).parent.mkdir(parents=True, exist_ok=True)
    (ws / 报告).write_text(审查报告(节点标题, [(段落[1], 段落[1])] if 高亮 else []), encoding="utf-8")
    引擎(ws, "generate", "--node", 节点标题, "--doc", 文书, "--review", 报告)
    return 文书


def 确认(ws, 节点标题, 原话):
    return 引擎(ws, "confirm", "--node", 节点标题, "--words", 原话)


def 办完(ws, 节点标题, 原话):
    出一版(ws, 节点标题)
    确认(ws, 节点标题, 原话)


def 归档(ws, 计划, 来源=None):
    """按计划调归档 CLI 搬 待归档/（或工作区外的 来源）里的件；计划写在工作区外的临时位置。"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        计划文件 = pathlib.Path(tmp) / "计划.json"
        计划文件.write_text(json.dumps(计划, ensure_ascii=False), encoding="utf-8")
        参数 = [ARCHIVE, "apply", "--plan", 计划文件]
        if 来源:
            参数 += ["--from", 来源]
        return run(ws, *参数)


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


def 写文书(路径, 段落, 高亮段=()):
    """写一份能被 python-docx 打开、引擎扫得出高亮的最小 docx。高亮段 给段落下标（从 0 起）。"""
    路径 = pathlib.Path(路径)
    路径.parent.mkdir(parents=True, exist_ok=True)
    段们 = "".join(_段(t, i in set(高亮段)) for i, t in enumerate(段落))
    文档 = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="%s"><w:body>%s</w:body></w:document>' % (_W, 段们))
    with zipfile.ZipFile(str(路径), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/document.xml", 文档)
    return 路径
