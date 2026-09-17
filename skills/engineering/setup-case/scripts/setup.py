#!/usr/bin/env python3
"""起手 CLI：在当前目录长出案件工作区的目录形状、按预设图或空图起图、写只记名与归属的指针块。

标准库零依赖，不 import 兄弟 skill：图的每一次写入都经 skill "graph" 的 scripts/graph.py 子进程，
它仍是 图.json 的唯一写入口；预设图的绝对路径经 skill "domain" 的 scripts/preset.py resolve
子进程取，两处两归属仍归它管。本脚本不含任何领域语义。

用法：
  python setup.py init [--preset <名> --owner 出厂|个人] [--no-card]
                       [--workspace <目录>] [--engine <graph.py>] [--preset-cli <preset.py>]
  python setup.py register --node <节点标题或 id> --file <工作区内相对路径>
                       [--workspace <目录>] [--engine <graph.py>]

init 的前置只有一条：工作区里没有 图.json（起手一案一次）。**目录非空不拒**：目录里
原有的文件与目录一律挪进 待归档/，等归档（调 skill "filing"）判去向。两条起手路二选一：不给
--preset 就是空图；给 --preset <名> 加 --owner 出厂|个人 就整份拷入那份预设图，它的 模板/ 一并
拷进 参考/模板/。顺序是先解析预设图、再落图、再建格：解析不到或引擎拒了，都是一格不建、一个字不写。
归档、起手清单不在这里，它们是别的 skill 与模型的事。

init 收尾还维护一份包外的个人文件：桌面卡片按 ~/.loo0ng/卡片设置.json 里的 根目录 列表扫
下面一层发现案件，本脚本把新工作区的上级目录加进那个列表。**文件不在就一个字不写**：那台机器
没有卡片，起手不替它长配置，也不在回显里提。加，不删不改，既有的一条不动、顺序不重排；
读不出、形状不对、写不进都只回一句，起手照样算完成。--no-card 整步不做。

register 是起手清单里「既有成品登记为已生成、来源律师」那一条的机械落地：把那份成品挪进它
节点的文书目录、按固定一行写审查报告（每一版文书必有一份，格式归 skill "to-docx"），
再经引擎追加一条来源为律师的生成条目。它只登记不确认：确认永不自动。

退出码：0 完成；1 拒绝（图已存在、解析不到预设图、引擎拒写、找不到文件、路径越界、目标已被占）；2 用法错误。
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

GRAPH_FILENAME = "图.json"
VIEW_MD = "图视图.md"
VIEW_JSON = "图视图.json"
ARCHIVE_INDEX = "归档索引.md"
AGENTS_FILENAME = "AGENTS.md"
CLAUDE_FILENAME = "CLAUDE.md"
CLAUDE_MD_TEXT = "@AGENTS.md\n"
POINTER_HEADING = "# 案件工作区"

# 目录形状。文书/<模块>/<节点>/ 出件时才建。
CELLS = ("待归档", "材料", "参考/模板", "参考/指南", "文书")
PENDING = "待归档"
DOCS_CELL = "文书"
WORKSPACE_TEMPLATES = pathlib.Path("参考") / "模板"
PRESET_TEMPLATES_DIRNAME = "模板"

OWNER_FACTORY, OWNER_PERSONAL = "出厂", "个人"
OWNERS = (OWNER_FACTORY, OWNER_PERSONAL)
EMPTY_LABEL = "无（空图起手）"

# 跨 skill 一律子进程互调、按兄弟目录找。
ENGINE_RELATIVE = pathlib.Path("..") / ".." / "graph" / "scripts" / "graph.py"
PRESET_CLI_RELATIVE = pathlib.Path("..") / ".." / "domain" / "scripts" / "preset.py"

AGENTS_TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "WORKSPACE-AGENTS.md"

# 律师自写文书的审查报告只记这一行：没有施加、没有高亮清单，下次重出读到它就知道
# 当前文书里的黄全是律师自己加的，一处不动。律师那句话不进这里：生成条目不存原话（引擎里
# 只有确认条目存），起手清单那一句留在对话与收尾里。
REVIEW_LINE = "律师自写\n"
REVIEW_SUFFIX = "-审查报告.md"

# 起手自己落的那几样不挪进待归档；点开头的（.git、.codex 之类）也不动。
KEEP_AT_ROOT = {GRAPH_FILENAME, VIEW_MD, VIEW_JSON, ARCHIVE_INDEX, AGENTS_FILENAME, CLAUDE_FILENAME}

# 桌面卡片的个人设置。「家」那一层与个人预设图同一个：环境变量换的是家，不是这个文件名。
PERSONAL_HOME_ENV = "LOO0NG_HOME"
PERSONAL_HOME_DIRNAME = ".loo0ng"
CARD_SETTINGS_FILENAME = "卡片设置.json"
CARD_ROOTS_KEY = "根目录"


class Rejected(Exception):
    """拒绝：图已存在、解析不到预设图、引擎拒写、找不到文件、路径越界、目标已被占。"""


def resolve_tool(given: Optional[str], relative: pathlib.Path, what: str, flag: str) -> pathlib.Path:
    tool = pathlib.Path(given).resolve() if given else (
        pathlib.Path(__file__).resolve().parent / relative).resolve()
    if not tool.is_file():
        raise Rejected("找不到%s %s；用 %s 指向它" % (what, tool, flag))
    return tool


def run_tool(tool: pathlib.Path, args: List[str]) -> Tuple[int, str, str]:
    """跨 skill 一律这一条路：子进程调它的 CLI，回（退出码, stdout, stderr）。"""
    r = subprocess.run([sys.executable, str(tool), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def run_engine(engine: pathlib.Path, graph_path: pathlib.Path, args: List[str]) -> Tuple[int, str, str]:
    return run_tool(engine, ["--graph", str(graph_path), *args])


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_workspace_relative(value: str, label: str) -> None:
    """相对工作区根的正斜杠路径，与引擎同一条规矩：绝对路径、反斜杠、.. 一律拒。"""
    if not value:
        raise Rejected("%s 不能为空" % label)
    if "\\" in value:
        raise Rejected("%s 用正斜杠写相对工作区根的路径，收到 %r" % (label, value))
    path = pathlib.PurePosixPath(value)
    if path.is_absolute() or (len(value) > 1 and value[1] == ":"):
        raise Rejected("%s 须是相对工作区根的路径，不能是绝对路径，收到 %r" % (label, value))
    if ".." in path.parts:
        raise Rejected("%s 不能越出工作区，收到 %r" % (label, value))


# ---------------------------------------------------------------- init

def resolve_preset(preset_cli: pathlib.Path, name: str, owner: str) -> Tuple[pathlib.Path, List[str]]:
    """子进程调 skill "domain" 的 preset.py resolve 取那份预设图的绝对路径。

    与调图引擎是同一个形状：两处两归属归它管，本脚本既不自己算路径，也不把路径记进工作区。
    它发生在落图与建格之前：resolve 拒了这里跟着拒，一格不建、一个字不写。回显原样带回去。
    """
    code, out, err = run_tool(preset_cli, ["resolve", "--name", name, "--owner", owner])
    lines = [line for line in out.splitlines() if line.strip()]
    if code != 0:
        raise Rejected("解析不到%s预设图「%s」，工作区一格没建、一个字没写：%s" % (owner, name, err or out))
    if not lines:
        raise Rejected("preset.py resolve 该回一行绝对路径，什么都没回")
    directory = pathlib.Path(lines[0].strip()).resolve()
    if not directory.is_dir():
        raise Rejected("preset.py resolve 回的 %s 不是一个目录" % directory)
    return directory, lines[1:]


def make_cells(ws: pathlib.Path) -> None:
    for cell in CELLS:
        (ws / cell).mkdir(parents=True, exist_ok=True)


def sweep_to_pending(ws: pathlib.Path) -> List[str]:
    """目录里原有的一律挪进 待归档/：起手不判它们是什么，判去向是归档的事（调 skill "filing"）。

    **在建格之前跑**：律师原本就有一个叫 材料/ 或 文书/ 的目录时，那也是他自己堆的东西，
    要一样进待归档让归档判去向；建完格再扫就会把它们当成格跳过，律师从此看不见它们。

    不动两类：起手自己落的那几样（图、两份视图、归档索引、两份指针块）、点开头的
    （.git、.codex 之类工具自己的东西）。待归档里已经有同名的就留在原处并报一句。
    """
    pending = ws / PENDING
    pending.mkdir(parents=True, exist_ok=True)
    moved, dotted, clashed = [], [], []
    for entry in sorted(ws.iterdir(), key=lambda p: p.name):
        name = entry.name
        if name in KEEP_AT_ROOT or name == PENDING:
            continue
        if name.startswith("."):
            dotted.append(name)
            continue
        target = pending / name
        if target.exists():
            clashed.append(name)
            continue
        shutil.move(str(entry), str(target))
        moved.append(name)
    notes = ["工作区根上原有的 %d 件已挪进 %s/：%s" % (len(moved), PENDING, "、".join(moved))
             if moved else "工作区根上没有要挪进 %s/ 的东西" % PENDING]
    if clashed:
        notes.append("这 %d 件在 %s/ 下已经有同名的，留在工作区根没动：%s"
                     % (len(clashed), PENDING, "、".join(clashed)))
    if dotted:
        notes.append("点开头的 %d 项没动（工具自己的东西）：%s" % (len(dotted), "、".join(dotted)))
    return notes


def copy_preset_templates(ws: pathlib.Path, preset_dir: pathlib.Path) -> List[str]:
    """预设图的 模板/ 整份拷进 参考/模板/：不改名、不覆盖、子目录相对路径原样。"""
    source = preset_dir / PRESET_TEMPLATES_DIRNAME
    target = ws / WORKSPACE_TEMPLATES
    if not source.is_dir():
        return ["预设图 %s 下没有 %s/，一件模板没拷：挂着模板的节点出件前要补"
                % (preset_dir.as_posix(), PRESET_TEMPLATES_DIRNAME)]
    copied, skipped = 0, []
    for src in sorted(p for p in source.rglob("*") if p.is_file()):
        dst = target / src.relative_to(source)
        if dst.exists():
            skipped.append(src.relative_to(source).as_posix())
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(src), str(dst))
        copied += 1
    notes = ["已从预设图拷 %d 件空白模板进 %s/" % (copied, WORKSPACE_TEMPLATES.as_posix())]
    if skipped:
        notes.append("这 %d 件 %s/ 下已经有同名的，没覆盖：%s"
                     % (len(skipped), WORKSPACE_TEMPLATES.as_posix(), "、".join(skipped)))
    return notes


def read_utf8(path: pathlib.Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def put_beside(path: pathlib.Path, block: str, marker: str, at_end: bool) -> str:
    """把一块字写进 path：没有那份文件就新建，有就按 at_end 追加在末尾或加在开头，
    **原有内容一字不动**；已经有 marker 就一个字不写。回一句给律师看的话。"""
    if not path.is_file():
        path.write_text(block, encoding="utf-8")
        return "已写 %s" % path.name
    old = read_utf8(path)
    if old is None:
        return "%s 读不出（不是 UTF-8），没往里写：手工把下面这一块加进去。\n%s" % (path.name, block)
    if marker in old:
        return "%s 里已经有「%s」，没有再写一遍" % (path.name, marker.strip())
    path.write_text(old.rstrip("\n") + "\n\n" + block if at_end else block + old.lstrip("\n"),
                    encoding="utf-8")
    return "已把这一块%s已有的 %s，原有内容一字未动" % ("追加到" if at_end else "加在", path.name)


def write_pointer_block(ws: pathlib.Path, preset_label: str) -> List[str]:
    """指针块只记四项，一条路径都不记：包一升级绝对路径就死，路径每次按名当场解析。

    AGENTS.md 给 Codex 读，CLAUDE.md 一行引它给 Claude Code 读。目录里原本就有这两份的（Codex
    建的项目常有），那是律师或 Codex 自己写的项目说明，原文一字不动。
    块由起手那一问机械推出，不加确认点；之后没有任何 skill 往里写。
    """
    block = AGENTS_TEMPLATE.read_text(encoding="utf-8").format(预设图=preset_label)
    return [put_beside(ws / AGENTS_FILENAME, block, POINTER_HEADING, at_end=True),
            put_beside(ws / CLAUDE_FILENAME, CLAUDE_MD_TEXT, CLAUDE_MD_TEXT.strip(), at_end=False)]


# ------------------------------------------------------- 桌面卡片的根目录设置

def personal_home() -> pathlib.Path:
    """个人文件的家：默认 ~/.loo0ng/。环境变量 LOO0NG_HOME 换的是「家」那一层。"""
    given = os.environ.get(PERSONAL_HOME_ENV)
    return pathlib.Path(given).expanduser() if given else pathlib.Path.home() / PERSONAL_HOME_DIRNAME


def same_dir(given: str, target: pathlib.Path) -> bool:
    """设置里的一条根目录指的是不是 target。只做路径归一，不碰盘上的东西。"""
    try:
        left = pathlib.Path(given).expanduser().absolute()
    except (OSError, ValueError):
        return False
    here = os.path.normcase(os.path.normpath(str(left)))
    there = os.path.normcase(os.path.normpath(str(target)))
    return here == there


def maintain_card_roots(ws: pathlib.Path) -> List[str]:
    """把工作区的上级目录加进桌面卡片的根目录列表。加，不删不改；出什么事都不挡起手。"""
    settings = personal_home() / CARD_SETTINGS_FILENAME
    if not settings.is_file():
        return []                      # 这台机器没有卡片：不创建、不回显
    parent = ws.parent
    hand_edit = "要让这一案出现在卡片上，自己把 %s 加进它的 %s。" % (parent, CARD_ROOTS_KEY)
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["桌面卡片的设置读不出或不是有效的 UTF-8 JSON，没动它：%s。%s" % (settings, hand_edit)]
    roots = data.get(CARD_ROOTS_KEY) if isinstance(data, dict) else None
    if not isinstance(roots, list) or any(not isinstance(root, str) for root in roots):
        return ['桌面卡片的设置里没有可用的 %s 列表，没动它：%s。把它写成 {"%s": ["%s"]}。'
                % (CARD_ROOTS_KEY, settings, CARD_ROOTS_KEY, parent.as_posix())]
    if any(same_dir(root, parent) for root in roots):
        return ["桌面卡片已经在看 %s，设置没动" % parent]
    data[CARD_ROOTS_KEY] = roots + [parent.as_posix()]
    tmp = settings.with_name(settings.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(settings))
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return ["桌面卡片的设置写不进，没动它：%s。%s" % (settings, hand_edit)]
    return ["桌面卡片的根目录已加上 %s：下一轮扫描就能看见这一案" % parent]


def cmd_init(args) -> int:
    ws = pathlib.Path(args.workspace).resolve()
    graph_path = ws / GRAPH_FILENAME
    if graph_path.exists():
        raise Rejected("%s 已经有 %s 了：起手一案一次。这个目录已经是案件工作区，"
                       "要改图的构成在对话里说一句就行，要另起一案换一个目录。" % (ws, GRAPH_FILENAME))
    if bool(args.preset) != bool(args.owner):
        raise Rejected("--preset 与 --owner 同给同不给：不给就是空图起手，给就要两个都给"
                       "（--preset <名> --owner 出厂|个人）。名与归属打 skill \"domain\" 的 "
                       "preset.py list 看两组各有哪些。")
    engine = resolve_tool(args.engine, ENGINE_RELATIVE, "图引擎", "--engine")
    preset_dir, preset_notes = None, []
    if args.preset:
        preset_cli = resolve_tool(args.preset_cli, PRESET_CLI_RELATIVE,
                                  "skill \"domain\" 的 preset.py", "--preset-cli")
        preset_dir, preset_notes = resolve_preset(preset_cli, args.preset, args.owner)

    ws.mkdir(parents=True, exist_ok=True)
    init_args = ["init", "--empty"] if preset_dir is None else ["init", "--preset", str(preset_dir)]
    code, out, err = run_engine(engine, graph_path, init_args)
    if code != 0:
        raise Rejected("图引擎没起手，工作区一格没建：%s" % (err or out))

    notes = preset_notes + ([out] if out else [])
    notes += sweep_to_pending(ws)   # 先扫再建格：原有的 材料/、文书/ 也要进待归档
    make_cells(ws)
    notes.append("目录形状已建：%s" % "、".join(CELLS))
    if preset_dir is not None:
        notes += copy_preset_templates(ws, preset_dir)
    else:
        notes.append("空图起手，不拷模板：%s/ 先空着，律师自己的空白模板经归档放进来"
                     % WORKSPACE_TEMPLATES.as_posix())
    label = EMPTY_LABEL if preset_dir is None else "%s（%s）" % (args.preset, args.owner)
    notes += write_pointer_block(ws, label)
    notes.append("两份视图已随图落下：%s、%s" % (VIEW_MD, VIEW_JSON))
    if not args.no_card:
        notes += maintain_card_roots(ws)
    for line in notes:
        print(line)
    return 0


# ---------------------------------------------------------------- register

def locate_node(ws: pathlib.Path, key: str) -> Tuple[str, str, str]:
    """回（模块目录名, 节点目录名, 节点标题）。目录名取 图视图.json 里引擎算好的那一份：
    标题做目录名的转义规则只定一次，在引擎里，本脚本不自己再实现一遍。"""
    view_path = ws / VIEW_JSON
    if not view_path.is_file():
        raise Rejected("%s 里没有 %s：先起手（setup.py init），或调用 Skill 工具，传 \"graph\"，重算视图"
                       % (ws, VIEW_JSON))
    try:
        view = read_json(view_path)
    except (OSError, ValueError) as e:
        raise Rejected("%s 读不出：%s" % (VIEW_JSON, e)) from e
    for m in view.get("模块", []):
        for n in m.get("节点", []):
            if key in (n.get("标题"), n.get("id")):
                return m["目录名"], n["目录名"], n["标题"]
    raise Rejected("图里没有节点「%s」：既有成品要登记到图上已有的节点，先调用 Skill 工具，传 \"graph\"，"
                   "新增一个，再登记。" % key)


def undo_register(source: pathlib.Path, doc_path: pathlib.Path,
                  review_path: pathlib.Path, made_dirs: bool) -> None:
    """引擎拒了就把这一次做过的两件事撤回去：成品挪回原处、审查报告删掉、空出来的目录收掉。"""
    if review_path.exists():
        review_path.unlink()
    if doc_path.exists():
        shutil.move(str(doc_path), str(source))
    if made_dirs:
        for d in (doc_path.parent, doc_path.parent.parent):
            try:
                d.rmdir()
            except OSError:
                break


def cmd_register(args) -> int:
    ws = pathlib.Path(args.workspace).resolve()
    if not (ws / GRAPH_FILENAME).is_file():
        raise Rejected("%s 里没有 %s：先起手（setup.py init）" % (ws, GRAPH_FILENAME))
    module_dir, node_dir, title = locate_node(ws, args.node)
    check_workspace_relative(args.file, "--file")
    source = ws / args.file
    if not source.is_file():
        raise Rejected("找不到 %s。既有成品要在工作区里，路径相对工作区根写。" % args.file)

    doc_dir = "%s/%s/%s" % (DOCS_CELL, module_dir, node_dir)
    doc_rel = "%s/%s%s" % (doc_dir, node_dir, source.suffix)
    review_rel = "%s/%s%s" % (doc_dir, node_dir, REVIEW_SUFFIX)
    doc_path, review_path = ws / doc_rel, ws / review_rel
    if doc_path.exists():
        raise Rejected("%s 已经有了，登记不覆盖：那个节点已经有一份文书，要换一版由律师自己打 doit。"
                       % doc_rel)
    engine = resolve_tool(args.engine, ENGINE_RELATIVE, "图引擎", "--engine")

    made_dirs = not doc_path.parent.exists()
    try:
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(doc_path))
        review_path.write_text(REVIEW_LINE, encoding="utf-8")
    except OSError as e:
        undo_register(source, doc_path, review_path, made_dirs)
        raise Rejected("挪不进 %s：%s。节点标题做目录名用不了的字由引擎换成全角，"
                       "仍不行就先改标题（调用 Skill 工具，传 \"graph\"）。" % (doc_dir, e)) from e

    code, out, err = run_engine(engine, ws / GRAPH_FILENAME, [
        "generate", "--node", title, "--doc", doc_rel, "--review", review_rel, "--lawyer-written"])
    if code != 0:
        undo_register(source, doc_path, review_path, made_dirs)
        raise Rejected("引擎没写条目，成品已挪回 %s、审查报告已撤回：%s" % (args.file, err or out))
    print(out or "已追加生成条目")
    print("已把 %s 挪成 %s，并写审查报告 %s（固定一行「%s」）：这一版是起手前已有的成品，"
          "本工作台没有参与写作。" % (args.file, doc_rel, review_rel, REVIEW_LINE.strip()))
    return 0


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="setup.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace", default=".", help="案件工作区，默认当前目录")
    common.add_argument("--engine", default=None,
                        help="图引擎 graph.py 的路径，默认取兄弟 skill graph 里的")

    p = sub.add_parser("init", parents=[common],
                       help="建目录形状、起图（空图或整份拷入预设图）、拷模板、挪待归档、写指针块")
    p.add_argument("--preset", default=None,
                   help="预设图的名；不给就是空图起手。与 --owner 同给同不给")
    p.add_argument("--owner", default=None, choices=OWNERS,
                   help="预设图的归属：出厂（包内）或 个人（本机）")
    p.add_argument("--no-card", dest="no_card", action="store_true",
                   help="不维护桌面卡片的根目录设置（默认：那份设置在就把上级目录加进去）")
    p.add_argument("--preset-cli", dest="preset_cli", default=None,
                   help="skill \"domain\" 的 preset.py 路径，默认取兄弟目录里的")

    p = sub.add_parser("register", parents=[common], help="把既有成品登记为已生成、来源律师")
    p.add_argument("--node", required=True, help="节点标题或 id")
    p.add_argument("--file", required=True, help="既有成品在工作区里的相对路径（如 待归档/某件.docx）")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "init":
            return cmd_init(args)
        return cmd_register(args)
    except Rejected as e:
        print("拒绝：%s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
