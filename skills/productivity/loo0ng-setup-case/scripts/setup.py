#!/usr/bin/env python3
"""起手 CLI：在当前目录建案件工作区的六格、起手图三选一、拷官方模板原件、写工作区指针块。

标准库零依赖，不 import 兄弟 skill：图的每一次写入都经 skill "loo0ng-graph" 的 scripts/graph.py 子进程，
它仍是 图.json 的唯一写入口；--domain-name 的活图目录经 skill "loo0ng-domain" 的 scripts/sketch.py home
子进程取，活图仍归它管。本脚本不含任何领域语义，六格与指针块的形状见 ../references/。

用法：
  python setup.py init --empty | --full | --from <定制图>
                       [--domain-name <领域名> | --domain <领域目录或其中的领域图.json>]
                       [--name <领域名>] [--workspace <目录>] [--engine <graph.py>] [--sketch <sketch.py>]
  python setup.py register --node <节点标题> --doc <工作区内相对路径> --words "<律师那句话>"
                       [--domain <领域目录或领域图.json>] [--workspace <目录>] [--engine <graph.py>]

init 的前置是工作区里没有 图.json，有就拒绝：起手一案一次（ADR-0007）。领域目录两种传法二选一：
律师侧给 --domain-name <领域名>（路径本脚本自己取，只打这一条命令），开发侧给 --domain <路径>
（种子回放、开发者定制的领域目录）。顺序是先取活图、再落图、再建格：取不到活图或引擎拒了，
都是一格不建、一个字不写。归档、雏形、起手清单不在这里，它们是别的 skill 与模型的事。

register 是起手清单里「既有成品登记为已生成、来源律师」那一条的机械落地：按固定模板写一份
审查报告（每一版文书必有一份，CONTEXT.md「审查报告」），再经引擎追加一条来源为律师的生成条目。
它只登记不确认：确认永不自动（ADR-0002）。

退出码：0 完成；1 拒绝（图已存在、三选一没选一个、取不到活图、引擎拒写、找不到文件、路径越界）；2 用法错误。
"""
import argparse
import datetime as _dt
import json
import pathlib
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

GRAPH_FILENAME = "图.json"
VIEW_MD = "图视图.md"
VIEW_JSON = "图视图.json"
DOMAIN_GRAPH_FILENAME = "领域图.json"
DOMAIN_TEMPLATES_DIRNAME = "模板"
SEED_ASSETS_DIRNAME = "assets"        # skill 包内的出厂种子（ADR-0019），不是活图
SEED_SKILL_DIRNAME = "loo0ng-domain"
SEED_ROOT_RELATIVE = pathlib.Path("..") / ".." / SEED_SKILL_DIRNAME / SEED_ASSETS_DIRNAME
ENGINE_RELATIVE = pathlib.Path("..") / ".." / "loo0ng-graph" / "scripts" / "graph.py"
SKETCH_RELATIVE = pathlib.Path("..") / ".." / SEED_SKILL_DIRNAME / "scripts" / "sketch.py"
LIVE_PREFIX = "活图："   # sketch.py home 回显的第一行，路径跟在它后面
REFERENCES = pathlib.Path(__file__).resolve().parent.parent / "references"
AGENTS_TEMPLATE = REFERENCES / "工作区AGENTS.md"
REVIEW_TEMPLATE = REFERENCES / "既有成品审查报告.md"
CLAUDE_MD_TEXT = "@AGENTS.md\n"
NO_DOMAIN_TEXT = "（无：起手时没有给领域目录。要前方、惰性带入与时限，让开发者把领域目录的绝对路径补进这一行）"

# 六格（ADR-0007）。材料/ 由 材料/律师陈述 一并建出；文书/<节点标题>/ 出件时才建。
CELLS = ("收件箱", "材料/律师陈述", "指南", "模板/官方", "模板/生成", "文书")
OFFICIAL_TEMPLATES_CELL = "模板/官方"


class Rejected(Exception):
    """拒绝：图已存在、三选一没选一个、引擎拒写、找不到文件、路径越界。"""


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def default_engine() -> pathlib.Path:
    return (pathlib.Path(__file__).resolve().parent / ENGINE_RELATIVE).resolve()


def resolve_engine(given: Optional[str]) -> pathlib.Path:
    engine = pathlib.Path(given).resolve() if given else default_engine()
    if not engine.is_file():
        raise Rejected("找不到图引擎 %s；用 --engine 指向 skill \"loo0ng-graph\" 的 scripts/graph.py" % engine)
    return engine


def default_sketch() -> pathlib.Path:
    return (pathlib.Path(__file__).resolve().parent / SKETCH_RELATIVE).resolve()


def resolve_sketch(given: Optional[str]) -> pathlib.Path:
    sketch = pathlib.Path(given).resolve() if given else default_sketch()
    if not sketch.is_file():
        raise Rejected("找不到 %s；用 --sketch 指向 skill \"loo0ng-domain\" 的 scripts/sketch.py，"
                       "或改用 --domain <领域目录> 直接给路径" % sketch)
    return sketch


def live_domain_dir(sketch: pathlib.Path, name: str) -> Tuple[pathlib.Path, List[str]]:
    """--domain-name 走这条：子进程调 skill "loo0ng-domain" 的 sketch.py home 取活图目录（ADR-0019）。

    与图引擎同一个形状：活图归 skill "loo0ng-domain" 管，本脚本只是调用者，不自己算活图在哪、
    也不自己拷种子。它发生在建格与落图之前：home 拒了这里跟着拒，一格不建、一个字不写。
    home 的回显原样带回去，首次起手拷了几件是律师该看见的。
    """
    r = subprocess.run([sys.executable, str(sketch), "home", "--name", name], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    lines = [line for line in (r.stdout or "").splitlines() if line.strip()]
    if r.returncode != 0:
        raise Rejected("取不到领域「%s」的活图目录，工作区一格没建、一个字没写：%s"
                       % (name, (r.stderr or r.stdout).strip()))
    if not lines or not lines[0].startswith(LIVE_PREFIX):
        raise Rejected("sketch.py home 的回显第一行该是「%s<绝对路径>」，收到 %r"
                       % (LIVE_PREFIX, lines[0] if lines else ""))
    return pathlib.Path(lines[0][len(LIVE_PREFIX):].strip()).resolve(), lines


def resolve_domain_dir(given: Optional[str]) -> Optional[pathlib.Path]:
    """--domain 收领域目录或其中的 领域图.json，指针块里记的一律是目录。"""
    if not given:
        return None
    path = pathlib.Path(given).resolve()
    return path.parent if path.suffix.lower() == ".json" else path


def looks_like_seed(domain_dir: pathlib.Path) -> bool:
    """两条判据取或：兄弟 skill 的 assets/ 下（按本脚本的位置算，装在哪儿都成立），
    或者目录名摆成 <...>/loo0ng-domain/assets/<领域名>（别处拷来的一份包）。"""
    sibling = (pathlib.Path(__file__).resolve().parent / SEED_ROOT_RELATIVE).resolve()
    try:
        domain_dir.relative_to(sibling)
        return True
    except ValueError:
        pass
    return (domain_dir.parent.name == SEED_ASSETS_DIRNAME
            and domain_dir.parent.parent.name == SEED_SKILL_DIRNAME)


def seed_path_note(domain_dir: Optional[pathlib.Path]) -> List[str]:
    """--domain 指到 skill 包内的出厂种子上时说一句（ADR-0019）。只报不拒：起手是读，开发侧的种子回放
    本来就直接对着种子起手；写那一刻另有引擎无条件拒着（ADR-0020），这里不必再拦一次。
    错在律师起手上时，这一行是它唯一会露头的地方。"""
    if domain_dir is None or not looks_like_seed(domain_dir):
        return []
    return ["注意：--domain 给的是 skill 包内的出厂种子，不是活图（ADR-0019）：包一升级它就被换掉，"
            "律师累计的东西不在这里。律师起手改用 --domain-name <领域名>，活图路径由本脚本自己经 "
            "skill \"loo0ng-domain\" 的 sketch.py home 取。"]


def engine_base(graph_path: pathlib.Path, domain_dir: Optional[pathlib.Path]) -> List[str]:
    base = ["--graph", str(graph_path)]
    if domain_dir is not None:
        base += ["--domain", str(domain_dir)]
    return base


def run_engine(engine: pathlib.Path, base: List[str], args: List[str]) -> Tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(engine), *base, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def read_graph(graph_path: pathlib.Path) -> dict:
    return json.loads(graph_path.read_text(encoding="utf-8"))


def nodes_of(data: dict):
    for m in data.get("模块", []):
        for n in m.get("节点", []):
            yield n


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

def make_cells(ws: pathlib.Path) -> None:
    for cell in CELLS:
        (ws / cell).mkdir(parents=True, exist_ok=True)


def copy_official_templates(ws: pathlib.Path, data: dict, domain_dir: Optional[pathlib.Path]) -> List[str]:
    """把起手图上挂到的官方模板原件从领域目录拷进 模板/官方/。惰性：图上没挂的不拷。
    缺原件只报不拒：领域目录可以没有 模板/（合成小领域就没有）。"""
    wanted = sorted({n["空白模板"]["文件"] for n in nodes_of(data)
                     if isinstance(n.get("空白模板"), dict) and n["空白模板"].get("来源") == "官方"})
    if not wanted:
        return ["起手图上没有节点挂官方模板，%s/ 先空着。" % OFFICIAL_TEMPLATES_CELL]
    if domain_dir is None:
        return ["起手时没有给领域目录，起手图挂到的 %d 件官方模板原件没拷进来：%s" % (len(wanted), "、".join(wanted))]
    src_dir = domain_dir / DOMAIN_TEMPLATES_DIRNAME
    if not src_dir.is_dir():
        return ["领域目录 %s 下没有 %s/，起手图挂到的 %d 件官方模板原件没拷进来：%s"
                % (domain_dir.as_posix(), DOMAIN_TEMPLATES_DIRNAME, len(wanted), "、".join(wanted))]
    copied, missing = [], []
    for name in wanted:
        src = src_dir / name
        if src.is_file():
            shutil.copy2(src, ws / OFFICIAL_TEMPLATES_CELL / name)
            copied.append(name)
        else:
            missing.append(name)
    notes = ["已从领域目录拷 %d 件官方模板原件进 %s/" % (len(copied), OFFICIAL_TEMPLATES_CELL)]
    if missing:
        notes.append("领域目录里找不到这 %d 件模板原件，挂着它们的节点出件前要补：%s"
                     % (len(missing), "、".join(missing)))
    return notes


def write_pointer_block(ws: pathlib.Path, data: dict, domain_dir: Optional[pathlib.Path]) -> List[str]:
    """机制 B（ADR-0009）：AGENTS.md 给 Codex 读，CLAUDE.md 一行引它给 Claude Code 读。
    块由起手图三选一机械推出，不加确认点；之后没有任何 skill 往里写。"""
    text = AGENTS_TEMPLATE.read_text(encoding="utf-8").format(
        领域=data["领域"], 领域目录=domain_dir.as_posix() if domain_dir else NO_DOMAIN_TEXT)
    (ws / "AGENTS.md").write_text(text, encoding="utf-8")
    (ws / "CLAUDE.md").write_text(CLAUDE_MD_TEXT, encoding="utf-8")
    return ["已写工作区指针块 AGENTS.md 与一行 CLAUDE.md"]


def cmd_init(args) -> int:
    ws = pathlib.Path(args.workspace).resolve()
    graph_path = ws / GRAPH_FILENAME
    if graph_path.exists():
        raise Rejected("%s 已经有 %s 了：起手一案一次。这个目录已经是案件工作区，要改图的构成调用 "
                       "skill \"loo0ng-graph\"，要另起一案换一个空目录。" % (ws, GRAPH_FILENAME))
    chosen = sum(bool(x) for x in (args.empty, args.full, args.from_path))
    if chosen != 1:
        raise Rejected("起手图三选一，恰好给一个：--empty（空图）、--full（整份领域图）、"
                       "--from <定制图路径>（开发者交付的定制图）")
    if args.domain and args.domain_name:
        raise Rejected("--domain-name 与 --domain 二选一：律师侧给 --domain-name <领域名>，活图路径由本脚本"
                       "自己取；开发侧给 --domain <路径>（种子回放、开发者定制图）。")
    if args.domain_name and args.name:
        raise Rejected("--domain-name 已经给了领域名，不要再给 --name：两个给成不一样的，指针块的「领域」"
                       "与「领域目录」会各指一处。要另起一个领域名就改用 --domain <路径> 加 --name。")
    if args.full and not (args.domain or args.domain_name):
        raise Rejected("--full 要带 --domain-name <领域名>，或带 --domain 指向领域目录或其中的 %s"
                       % DOMAIN_GRAPH_FILENAME)
    engine = resolve_engine(args.engine)
    if args.domain_name:
        domain_dir, home_notes = live_domain_dir(resolve_sketch(args.sketch), args.domain_name)
    else:
        domain_dir, home_notes = resolve_domain_dir(args.domain), []

    ws.mkdir(parents=True, exist_ok=True)
    base = engine_base(graph_path, domain_dir)
    init_args = ["init"]
    if args.empty:
        init_args.append("--empty")
    elif args.full:
        init_args.append("--full")
    else:
        init_args += ["--from", str(pathlib.Path(args.from_path).resolve())]
    if args.name:
        init_args += ["--name", args.name]
    code, out, err = run_engine(engine, base, init_args)
    if code != 0:
        raise Rejected("图引擎没起手，工作区一格没建：%s" % (err or out))

    notes = home_notes + ([out] if out else [])
    make_cells(ws)
    notes.append("六格已建：%s" % "、".join(CELLS))
    data = read_graph(graph_path)
    notes += copy_official_templates(ws, data, domain_dir)
    notes += write_pointer_block(ws, data, domain_dir)
    notes += seed_path_note(domain_dir)
    notes.append("两份视图已随图落下：%s、%s" % (VIEW_MD, VIEW_JSON))
    for line in notes:
        print(line)
    return 0


# ---------------------------------------------------------------- register

def generated_versions(graph_path: pathlib.Path, node_title: str) -> int:
    """这个节点已经有几版：只读图数一遍生成条目。图里没有这个节点（要靠引擎按领域图带入）时算 0。

    版本号的算法归引擎（graph.py 的 versions），这里照算一次只为拼审查报告的文件名，不写进图；
    引擎哪天改了版本号的算法，这里的文件名会跟不上，`tests/loo0ng-setup-case/test_setup.py`
    的 test_审查报告按固定模板落在文书目录下 会红。"""
    try:
        data = read_graph(graph_path)
    except (OSError, ValueError):
        return 0
    for n in nodes_of(data):
        if n.get("标题") == node_title:
            return sum(1 for e in n.get("条目", []) if e.get("动作") == "生成")
    return 0


def cmd_register(args) -> int:
    ws = pathlib.Path(args.workspace).resolve()
    graph_path = ws / GRAPH_FILENAME
    if not graph_path.is_file():
        raise Rejected("%s 里没有 %s：先起手（setup.py init）" % (ws, GRAPH_FILENAME))
    title = args.node
    if "/" in title or "\\" in title:
        raise Rejected("节点标题里不能有斜杠：文书目录名就是节点标题（ADR-0007），收到 %r" % title)
    check_workspace_relative(args.doc, "--doc")
    if not (ws / args.doc).is_file():
        raise Rejected("找不到文书 %s。既有成品先经归档进工作区（调用 skill \"loo0ng-filing\"），再登记。" % args.doc)
    engine = resolve_engine(args.engine)
    domain_dir = resolve_domain_dir(args.domain)

    version = generated_versions(graph_path, title) + 1
    review_rel = "文书/%s/%s-v%d-审查报告.md" % (title, title, version)
    review_path = ws / review_rel
    made_dir = not review_path.parent.exists()
    try:
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(REVIEW_TEMPLATE.read_text(encoding="utf-8").format(
            节点=title, 版本=version, 文书=args.doc, 时间=now(), 原话=args.words), encoding="utf-8")
    except OSError as e:
        raise Rejected("写不了审查报告 %s：%s。文书目录名就是节点标题（ADR-0007），"
                       "标题里有文件名用不了的字就先改标题（调用 skill \"loo0ng-graph\"）。" % (review_rel, e)) from e

    code, out, err = run_engine(engine, engine_base(graph_path, domain_dir), [
        "generate", "--node", title, "--doc", args.doc, "--review", review_rel, "--lawyer-written"])
    if code != 0:
        review_path.unlink()
        if made_dir:
            try:
                review_path.parent.rmdir()
            except OSError:
                pass
        raise Rejected("引擎没写条目，审查报告已撤回：%s" % (err or out))
    print(out or "已追加生成条目")
    print("已按固定模板写审查报告 %s：这一版是起手前已有的成品，本工作台没有参与写作，也没跑门禁。" % review_rel)
    return 0


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="setup.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace", default=".", help="案件工作区，默认当前目录")
    common.add_argument("--engine", default=None,
                        help="图引擎 graph.py 的路径，默认取兄弟 skill loo0ng-graph 里的")
    common.add_argument("--domain", default=None,
                        help="领域目录或其中的 %s；开发侧那一条（种子回放、开发者定制图）。"
                             "律师侧用 --domain-name，别给包内 assets/ 下的出厂种子" % DOMAIN_GRAPH_FILENAME)

    p = sub.add_parser("init", parents=[common], help="建六格、起手图三选一、拷官方模板、写指针块")
    p.add_argument("--empty", action="store_true", help="空图起手")
    p.add_argument("--full", action="store_true", help="整份领域图起手（人的选择，不受惰性约束）")
    p.add_argument("--from", dest="from_path", default=None, help="开发者交付的定制图")
    p.add_argument("--domain-name", dest="domain_name", default=None,
                   help="领域名；活图目录由本脚本经 skill \"loo0ng-domain\" 的 sketch.py home 自己取。"
                        "律师侧用这一个，与 --domain 二选一")
    p.add_argument("--sketch", default=None,
                   help="sketch.py 的路径，默认取兄弟 skill loo0ng-domain 里的")
    p.add_argument("--name", default=None,
                   help="领域名；空图起手又没有 --domain / --domain-name 时必填。与 --domain-name 不并存")

    p = sub.add_parser("register", parents=[common], help="把既有成品登记为已生成、来源律师")
    p.add_argument("--node", required=True, help="节点标题")
    p.add_argument("--doc", required=True, help="文书相对工作区根的路径（归档后的位置）")
    p.add_argument("--words", required=True, help="律师拍板起手清单那句话，原样写进审查报告")
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
