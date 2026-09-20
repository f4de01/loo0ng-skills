#!/usr/bin/env python3
"""预设图的家：按名与归属解析路径、分两组列出、把当前案件图另存成一份个人预设图。

标准库零依赖，不 import 图引擎：另存的那一次写图仍只经 skill "graph" 的 scripts/graph.py 子进程。
本脚本不含任何领域语义：预设图的名只是一个目录名，图的形状由引擎说了算。

两处两归属：
  出厂  <本 skill>/assets/预设图/<名>/   预设图.json、模板/、指引手册/   随包分发，升级整个换掉，原位读、不拷出包
  个人  ~/.loo0ng/预设图/<名>/           预设图.json、模板/             律师另存而来，升级碰不到
两处不合并、同名不并存：另存与出厂重名即拒，让律师换个名字（起手列表两组同名会混）。

用法：
  python preset.py list    [--personal-root <目录>] [--factory-root <目录>]
  python preset.py resolve --name <名> --owner 出厂|个人 [--personal-root ...] [--factory-root ...]
  python preset.py save    --name <名> [--graph 图.json] [--templates 参考/模板]
                           [--engine graph.py] [--personal-root ...] [--factory-root ...]

list 分两组回显，起手用它给律师看；两组都空也照退 0，那是「只能从空图起手」。
resolve 回一行绝对路径：两处都没有这个名与归属就拒，不猜、不回退到另一个归属。
save 另存：先在同级的临时名上经引擎 export-preset 剥掉条目与不适用、再把 参考/模板/ 整份拷进去，
     两步都成了才改名到位；落到一半断了不会留下半份预设图。案件图一字不动。

退出码：0 完成；1 拒绝（找不到、重名、引擎拒写、名字不合法）；2 用法错误。
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

PRESET_FILENAME = "预设图.json"        # 与 skill "graph" 的引擎同一个名字，改一处要改两处
TEMPLATES_DIRNAME = "模板"
HANDBOOKS_DIRNAME = "指引手册"
WORKSPACE_TEMPLATES = pathlib.Path("参考") / TEMPLATES_DIRNAME
DEFAULT_GRAPH = "图.json"

OWNER_FACTORY, OWNER_PERSONAL = "出厂", "个人"
OWNERS = (OWNER_FACTORY, OWNER_PERSONAL)

PERSONAL_HOME_ENV = "LOO0NG_HOME"      # 「家」那一层；脚本层单测与 eval 用它，律师那台机上不设
PERSONAL_HOME_DIRNAME = ".loo0ng"
PRESET_DIRNAME = "预设图"              # 两处共用的那一层目录名：包内 assets/预设图/，本机 ~/.loo0ng/预设图/
# 包内出厂预设图的根。引擎按同一形状拒写它（graph.py 的 PRESET_ROOT_RELATIVE），改这里要改那一处。
FACTORY_ROOT_RELATIVE = pathlib.Path("..") / "assets" / PRESET_DIRNAME
# 兄弟 skill 的图引擎。跨 skill 一律子进程互调、按兄弟目录找（sketch.py 有同一行，改一处要改两处）。
ENGINE_RELATIVE = pathlib.Path("..") / ".." / "graph" / "scripts" / "graph.py"
STAGING_SUFFIX = ".另存中"


class Rejected(Exception):
    """拒绝：找不到预设图、与出厂重名、引擎拒写、名字不合法。案件图与已有的预设图一字不动。"""


# ---------------------------------------------------------------- 两处的根

def factory_root(given: Optional[str] = None) -> pathlib.Path:
    """出厂预设图根：本 skill 的 assets/预设图/，随包分发，升级时整个被换掉。"""
    if given:
        return pathlib.Path(given).resolve()
    return (pathlib.Path(__file__).resolve().parent / FACTORY_ROOT_RELATIVE).resolve()


def personal_root(given: Optional[str] = None) -> pathlib.Path:
    """个人预设图根：默认 ~/.loo0ng/预设图/。环境变量 LOO0NG_HOME 换的是「家」那一层。"""
    if given:
        return pathlib.Path(given).resolve()
    home = os.environ.get(PERSONAL_HOME_ENV, "").strip()
    base = pathlib.Path(home) if home else pathlib.Path.home() / PERSONAL_HOME_DIRNAME
    return (base / PRESET_DIRNAME).resolve()


def roots_of(args) -> List[Tuple[str, pathlib.Path]]:
    return [(OWNER_FACTORY, factory_root(args.factory_root)),
            (OWNER_PERSONAL, personal_root(args.personal_root))]


def root_of(owner: str, args) -> pathlib.Path:
    return dict(roots_of(args))[owner]


def check_name(name: str) -> str:
    """预设图的名就是一个目录名：不带路径分隔符，也不是 . 或 ..。"""
    if name in ("", ".", "..") or "/" in name or "\\" in name or ":" in name:
        raise Rejected("预设图的名是一个目录名，不能带路径分隔符，收到 %r" % name)
    return name


# ---------------------------------------------------------------- 读一份预设图

def read_preset(path: pathlib.Path):
    if not path.is_file():
        raise Rejected("找不到预设图 %s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise Rejected("%s 不是合法 JSON：%s" % (path, e)) from e


def counts(directory: pathlib.Path) -> str:
    """一份预设图的规模，只为回显：读不出就照实说，list 不因为一份坏图整条拒。"""
    try:
        data = read_preset(directory / PRESET_FILENAME)
        modules = data["模块"]
        nodes = sum(len(m["节点"]) for m in modules)
    except (Rejected, KeyError, TypeError) as e:
        return "读不出（%s）" % e
    templates = list((directory / TEMPLATES_DIRNAME).glob("*")) if (directory / TEMPLATES_DIRNAME).is_dir() else []
    return "%d 个模块、%d 个节点，模板 %d 件" % (len(modules), nodes, len(templates))


def presets_in(root: pathlib.Path) -> List[pathlib.Path]:
    if not root.is_dir():
        return []
    return sorted((d for d in root.iterdir() if (d / PRESET_FILENAME).is_file()), key=lambda d: d.name)


# ---------------------------------------------------------------- list / resolve

def cmd_list(args) -> int:
    total = 0
    for owner, root in roots_of(args):
        found = presets_in(root)
        total += len(found)
        print("%s（%s）：" % (owner, root.as_posix()))
        if not found:
            print("- （无）")
        for d in found:
            print("- %s：%s" % (d.name, counts(d)))
    if not total:
        print("两处都没有预设图：这次只能从空图起手。")
    return 0


def resolve_dir(name: str, owner: str, args) -> pathlib.Path:
    directory = root_of(owner, args) / check_name(name)
    if (directory / PRESET_FILENAME).is_file():
        return directory
    other = OWNER_PERSONAL if owner == OWNER_FACTORY else OWNER_FACTORY
    other_dir = root_of(other, args) / name
    hint = ("；%s那一处有同名的 %s，要它就把 --owner 改成 %s" % (other, other_dir.as_posix(), other)
            if (other_dir / PRESET_FILENAME).is_file() else
            "；%s那一处也没有。打 list 看两组各有哪些，一个都没有就从空图起手" % other)
    raise Rejected("%s预设图「%s」不在 %s 下%s" % (owner, name, root_of(owner, args).as_posix(), hint))


def cmd_resolve(args) -> int:
    directory = resolve_dir(args.name, args.owner, args)
    print(directory.as_posix())
    print("%s预设图「%s」：%s；%s" % (args.owner, args.name, counts(directory),
                                     "模板整份拷进 参考/模板/，指引手册留在包内给开发者导入用"
                                     if args.owner == OWNER_FACTORY else "模板整份拷进 参考/模板/"))
    return 0


# ---------------------------------------------------------------- save（另存）

def resolve_engine(given: Optional[str]) -> pathlib.Path:
    engine = pathlib.Path(given).resolve() if given else (
        pathlib.Path(__file__).resolve().parent / ENGINE_RELATIVE).resolve()
    if not engine.is_file():
        raise Rejected("找不到图引擎 %s；用 --engine 指向 skill \"graph\" 的 scripts/graph.py" % engine)
    return engine


def copy_templates(source: pathlib.Path, target: pathlib.Path) -> Tuple[int, List[str]]:
    """参考/模板/ 整份拷进预设图的 模板/：不改名、不覆盖、子目录相对路径原样。"""
    notes = []
    if not source.is_dir():
        return 0, ["工作区里没有 %s/，一件模板没拷：挂着模板的节点在别处起手时要补" % source.as_posix()]
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for src in sorted(p for p in source.rglob("*") if p.is_file()):
        dst = target / src.relative_to(source)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(src), str(dst))
        count += 1
    if not count:
        notes.append("%s/ 是空的，一件模板没拷" % source.as_posix())
    return count, notes


def cmd_save(args) -> int:
    name = check_name(args.name)
    graph_path = pathlib.Path(args.graph)
    if not graph_path.is_file():
        raise Rejected("找不到案件图 %s：另存要在案件工作区里跑" % graph_path)
    factory = factory_root(args.factory_root) / name
    if factory.exists():  # 看的是这个名占没占，不是那份图读不读得出：同名就是同名
        raise Rejected("出厂预设图里已经有「%s」（%s）：两处同名会让起手的列表分不清，换个名字再另存。"
                       "出厂件谁都不许写，另存永远落在个人预设图那一处。" % (name, factory.as_posix()))
    target = personal_root(args.personal_root) / name
    if target.exists():
        raise Rejected("%s 已经存在，另存不覆盖：换个名字，或先把旧的那份移走。" % target.as_posix())
    engine = resolve_engine(args.engine)

    # 建个人预设图的家也要在 try 里：它在包外，另存常跑在一个只许写工作目录的沙箱里，
    # 这一步就是第一个撞墙的地方。漏在外面，律师拿到的是一串 traceback 而不是一句话。
    staging = target.parent / ("%s%s-%d" % (name, STAGING_SUFFIX, os.getpid()))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(str(staging), ignore_errors=True)
        r = subprocess.run([sys.executable, str(engine), "--graph", str(graph_path), "export-preset",
                            "--out", str(staging)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise Rejected("引擎拒了另存，一个字没写：%s" % (r.stderr.strip() or r.stdout.strip()
                                                            or "引擎退出码 %d" % r.returncode))
        copied, notes = copy_templates(pathlib.Path(args.templates), staging / TEMPLATES_DIRNAME)
        os.replace(str(staging), str(target))
    except OSError as e:
        raise Rejected("另存没落成 %s：%s。案件图一字未动。" % (target.as_posix(), e)) from e
    finally:
        shutil.rmtree(str(staging), ignore_errors=True)

    engine_says = r.stdout.strip()
    if engine_says:
        print(engine_says.replace(str(staging), str(target)))
    print("已另存个人预设图「%s」：%s" % (name, target.as_posix()))
    print("模板拷了 %d 件进 %s/%s/；%s 一字未动。" % (copied, target.as_posix(), TEMPLATES_DIRNAME, graph_path.name))
    for note in notes:
        print(note)
    print("往后起手选它：归属「%s」，名「%s」。" % (OWNER_PERSONAL, name))
    return 0


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="preset.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--personal-root", default=None,
                        help="个人预设图根，默认 ~/.loo0ng/预设图（环境变量 %s 换「家」）" % PERSONAL_HOME_ENV)
    common.add_argument("--factory-root", default=None, help="出厂预设图根，默认本 skill 的 assets/预设图")

    sub.add_parser("list", parents=[common], help="分两组列出预设图，起手给律师看")

    p = sub.add_parser("resolve", parents=[common], help="按名与归属回一行绝对路径；没有即拒")
    p.add_argument("--name", required=True, help="预设图的名，如 破产")
    p.add_argument("--owner", required=True, choices=OWNERS, help="出厂（包内）或 个人（本机）")

    p = sub.add_parser("save", parents=[common], help="另存：把当前案件图剥成一份个人预设图，模板整份拷走")
    p.add_argument("--name", required=True, help="新预设图的名；与出厂同名即拒")
    p.add_argument("--graph", default=DEFAULT_GRAPH, help="案件图，默认当前目录的 图.json（只读）")
    p.add_argument("--templates", default=WORKSPACE_TEMPLATES.as_posix(),
                   help="工作区的空白模板目录，默认 参考/模板")
    p.add_argument("--engine", default=None, help="图引擎 graph.py 的路径，默认取兄弟 skill graph 里的")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "list":
            return cmd_list(args)
        if args.cmd == "resolve":
            return cmd_resolve(args)
        return cmd_save(args)
    except Rejected as e:
        print("拒绝：%s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
