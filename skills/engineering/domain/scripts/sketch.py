#!/usr/bin/env python3
"""雏形 CLI：把模型从一个来源提出的一批模块与节点，对着一张图判同名、回显，拍板后经图引擎写入。

标准库零依赖，不 import 图引擎：写入只经 skill "graph" 的 scripts/graph.py 子进程，它仍是图的唯一写入口。
本脚本不含任何领域语义：判重只看标题，写入只转交引擎。格式与规则见 ../SKETCH-FORMAT.md。

判重只做同名这一半（被检查的一方是模型自己写的雏形，归一化后的标题相等是集合成员）。
**相似不同名不由脚本判**：`check` 把图里现有的标题清单一并打出来，像不像由模型对着它自己判、
回显给拍板的人，判成同一个就把那条从雏形文件里删掉再 apply。脚本里没有相似度、没有阈值、没有待定。

用法：
  python sketch.py check --proposal 雏形.json [--graph 图.json] [--kind case|preset]
  python sketch.py apply --proposal 雏形.json [--graph 图.json] [--kind case|preset] [--engine graph.py]

check 只读：同名的挑掉，其余列进「新提出」，再打出图里现有的标题清单，图一字不动。
apply 拍板后跑：逐条交引擎写入，引擎的回显照抄；案件图上时限只回显不写：
      案件图的时限由起手从预设图整份拷入，律师不在案件图上写它；id 也只有预设图收。

退出码：0 完成；1 拒绝（雏形不合格式、引擎拒写、找不到文件）；2 用法错误。
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import unicodedata
from typing import Dict, List, Optional, Tuple

DEFAULT_GRAPH = "图.json"
# 兄弟 skill 的图引擎。跨 skill 一律子进程互调、按兄弟目录找（preset.py 有同一行，改一处要改两处）。
ENGINE_RELATIVE = pathlib.Path("..") / ".." / "graph" / "scripts" / "graph.py"
NO_TEMPLATE = "无"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

PROPOSAL_KEYS = {"模块", "来源"}
MODULE_KEYS = {"标题", "节点", "id"}
NODE_KEYS = {"标题", "空白模板", "时限", "id"}

STATUS_NEW, STATUS_EXISTING = "新", "已在图里"


class Rejected(Exception):
    """拒绝：雏形不合格式、引擎拒写、找不到文件。图一字不动（引擎拒了的那条除外，其余照写）。"""


# ---------------------------------------------------------------- 标题归一与同名

def normalize(title: str) -> str:
    """判同名用的标题：NFKC、小写、去空白与标点符号。"""
    text = unicodedata.normalize("NFKC", title).lower()
    return "".join(c for c in text if not c.isspace() and not unicodedata.category(c).startswith(("P", "S")))


def match(title: str, existing: List[str]) -> Tuple[str, Optional[str]]:
    """(已在图里 | 新, 图里对应的标题)。只判同名：像不像归模型，脚本不猜。"""
    key = normalize(title)
    for t in existing:
        if normalize(t) == key:
            return STATUS_EXISTING, t
    return STATUS_NEW, None


# ---------------------------------------------------------------- 读文件

def read_json(path: pathlib.Path, label: str):
    if not path.is_file():
        raise Rejected("找不到%s：%s" % (label, path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise Rejected("%s 不是合法 JSON：%s" % (label, e)) from e


def graph_titles(data) -> Tuple[List[str], List[str], Dict[str, str]]:
    """(模块标题, 节点标题, 节点标题 -> 所在模块标题)。只取标题，不做引擎那套校验（写入时引擎会校）。"""
    if not isinstance(data, dict) or not isinstance(data.get("模块"), list):
        raise Rejected("图的顶层须有 模块 数组")
    modules, nodes, owner = [], [], {}
    for m in data["模块"]:
        modules.append(m["标题"])
        for n in m.get("节点", []):
            nodes.append(n["标题"])
            owner[n["标题"]] = m["标题"]
    return modules, nodes, owner


# ---------------------------------------------------------------- 雏形文件

def parse_template(text) -> str:
    """校验空白模板写法（与引擎同一套：无，或一个文件名，不带路径），返回原样。"""
    if text == NO_TEMPLATE:
        return text
    if not isinstance(text, str) or not text.strip():
        raise Rejected("空白模板写法：无，或一个文件名，收到 %r" % (text,))
    if "/" in text or "\\" in text or ":" in text:
        raise Rejected("空白模板只写文件名，不带路径（文件住工作区的 参考/模板/ 或预设图的 模板/ 下），收到 %r" % text)
    return text


def _check_title(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Rejected("%s的标题须是非空字符串，收到 %r" % (what, value))
    return value.strip()


def _check_id(value, what: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not ID_RE.match(value):
        raise Rejected("%s的 id %r 不合法：只用字母、数字、连字符、下划线、点" % (what, value))
    return value


def load_proposal(path: pathlib.Path) -> dict:
    """读并校验雏形文件；雏形内部标题（归一后）不得重复。"""
    data = read_json(path, "雏形文件")
    if not isinstance(data, dict) or not (set(data) <= PROPOSAL_KEYS) or "模块" not in data:
        raise Rejected("雏形文件顶层键须是 模块（必有）与 来源（可选），实际：%s"
                       % (sorted(data) if isinstance(data, dict) else type(data).__name__))
    if not isinstance(data["模块"], list):
        raise Rejected("雏形文件的 模块 须是数组")
    modules = []
    seen_modules: Dict[str, str] = {}
    seen_nodes: Dict[str, str] = {}
    for m in data["模块"]:
        if not isinstance(m, dict) or not (set(m) <= MODULE_KEYS) or not ({"标题", "节点"} <= set(m)):
            raise Rejected("雏形里每个模块须有 标题 与 节点，可选 id；实际键：%s"
                           % (sorted(m) if isinstance(m, dict) else m))
        title = _check_title(m["标题"], "模块")
        key = normalize(title)
        if key in seen_modules:
            raise Rejected("雏形里模块「%s」与「%s」同名" % (title, seen_modules[key]))
        seen_modules[key] = title
        if not isinstance(m["节点"], list):
            raise Rejected("雏形里模块「%s」的 节点 须是数组" % title)
        nodes = []
        for n in m["节点"]:
            if not isinstance(n, dict) or not (set(n) <= NODE_KEYS) or not ({"标题", "空白模板"} <= set(n)):
                raise Rejected("雏形里模块「%s」下每个节点须有 标题 与 空白模板，可选 时限、id；实际键：%s" % (
                    title, sorted(n) if isinstance(n, dict) else n))
            nt = _check_title(n["标题"], "节点")
            nk = normalize(nt)
            if nk in seen_nodes:
                raise Rejected("雏形里节点「%s」与「%s」同名" % (nt, seen_nodes[nk]))
            seen_nodes[nk] = nt
            node = {"标题": nt, "空白模板": parse_template(n["空白模板"]),
                    "id": _check_id(n.get("id"), "节点「%s」" % nt)}
            if "时限" in n:
                if not isinstance(n["时限"], str) or not n["时限"].strip():
                    raise Rejected("节点「%s」的 时限 须是非空字符串" % nt)
                node["时限"] = n["时限"].strip()
            nodes.append(node)
        modules.append({"标题": title, "id": _check_id(m.get("id"), "模块「%s」" % title), "节点": nodes})
    return {"来源": data.get("来源"), "模块": modules}


# ---------------------------------------------------------------- 判同名

class Plan:
    """雏形对着一张图判同名后的结果：每个模块、节点标上状态与图里对应的标题。"""

    def __init__(self, proposal: dict, graph, kind: str):
        self.kind = kind
        self.source = proposal["来源"]
        self.graph_modules, self.graph_nodes, self.owner = graph_titles(graph)
        self.modules: List[dict] = []
        for m in proposal["模块"]:
            item = dict(m, 节点=[])
            item["状态"], item["对应"] = match(m["标题"], self.graph_modules)
            for n in m["节点"]:
                node = dict(n)
                node["状态"], node["对应"] = match(n["标题"], self.graph_nodes)
                item["节点"].append(node)
            self.modules.append(item)

    def has_time_limits(self) -> bool:
        return any("时限" in n for m in self.modules for n in m["节点"])

    def to_write(self) -> List[Tuple[str, dict, Optional[dict]]]:
        """要交给引擎的条目，按顺序：("module", m, None) 或 ("node", m, n)。已在图里的不写。"""
        items: List[Tuple[str, dict, Optional[dict]]] = []
        for m in self.modules:
            if m["状态"] == STATUS_NEW:
                items.append(("module", m, None))
            for n in m["节点"]:
                if n["状态"] == STATUS_NEW:
                    items.append(("node", m, n))
        return items


def render(plan: Plan, graph_name: str) -> str:
    kind_label = "预设图" if plan.kind == "preset" else "案件图"
    lines = ["# 雏形（对 %s，%s）" % (graph_name, kind_label), ""]
    if plan.source:
        lines += ["来源：%s" % plan.source, ""]
    new_lines, existing_lines = [], []
    for m in plan.modules:
        head = "- 模块「%s」（%s）" % (m["标题"], m["状态"])
        body = []
        for n in m["节点"]:
            if n["状态"] == STATUS_EXISTING:
                existing_lines.append("- 节点「%s」（图里在模块「%s」下）" % (n["标题"], plan.owner.get(n["对应"], "")))
                continue
            attrs = ["空白模板 %s" % n["空白模板"]]
            if "时限" in n:
                attrs.append("时限 %s" % n["时限"])
            body.append("  - 节点「%s」：%s" % (n["标题"], "；".join(attrs)))
        if body or m["状态"] != STATUS_EXISTING:
            new_lines.append(head)
            new_lines.extend(body)
    lines += ["## 新提出", ""]
    lines += new_lines or ["（无）"]
    lines.append("")
    if existing_lines:
        lines += ["## 已在图里，不重复提出（同名）", ""] + existing_lines + [""]
    lines += ["## 图里现有的标题（判相似用）", "",
              "模块：%s" % ("、".join(plan.graph_modules) or "（无）"),
              "节点：%s" % ("、".join(plan.graph_nodes) or "（无）"), "",
              "同名的上面已经挑掉了。相似不同名的脚本不判：对着这份清单自己看，"
              "判成同一个就把那条从雏形文件里删掉；判不准的写进回显让人定，拍板之后再 apply。", ""]
    if plan.kind == "case" and plan.has_time_limits():
        lines += ["时限只回显、案件图不存：案件图的时限由起手从预设图整份拷入，"
                  "通用的写进预设图，本案的具体日期是案件事实，走 材料/律师说过的.md。", ""]
    lines.append("拍板前 %s 一字未动。" % graph_name)
    return "\n".join(lines)


# ---------------------------------------------------------------- 引擎子进程

def resolve_engine(given: Optional[str]) -> pathlib.Path:
    engine = pathlib.Path(given).resolve() if given else (
        pathlib.Path(__file__).resolve().parent / ENGINE_RELATIVE).resolve()
    if not engine.is_file():
        raise Rejected("找不到图引擎 %s；用 --engine 指向 skill \"graph\" 的 scripts/graph.py" % engine)
    return engine


def engine_commands(plan: Plan, kind: str) -> List[Tuple[str, List[str]]]:
    """(条目描述, 引擎子命令参数)。案件图上不传 --id 与 --time-limit：id 由引擎生成，时限只写预设图。"""
    cmds = []
    for what, m, n in plan.to_write():
        if what == "module":
            args = ["add-module", "--title", m["标题"]]
            if m["id"]:
                args += ["--id", m["id"]]
            cmds.append(("模块「%s」" % m["标题"], args))
            continue
        module_key = m["对应"] if m["状态"] == STATUS_EXISTING else m["标题"]
        args = ["add-node", "--module", module_key, "--title", n["标题"], "--template", n["空白模板"]]
        if n["id"]:
            args += ["--id", n["id"]]
        if kind == "preset" and "时限" in n:
            args += ["--time-limit", n["时限"]]
        cmds.append(("节点「%s」" % n["标题"], args))
    return cmds


def run_engine(engine: pathlib.Path, base: List[str], args: List[str]) -> Tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(engine), *base, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ---------------------------------------------------------------- 两个子命令

def build_plan(args) -> Tuple[Plan, pathlib.Path]:
    graph_path = pathlib.Path(args.graph)
    proposal = load_proposal(pathlib.Path(args.proposal))
    graph = read_json(graph_path, "图")
    if args.kind == "case":
        with_id = ([x["标题"] for x in proposal["模块"] if x["id"]]
                   + [n["标题"] for x in proposal["模块"] for n in x["节点"] if n["id"]])
        if with_id:
            raise Rejected("案件图里的 id 由引擎生成，雏形里不能给 id（只有 --kind preset 收）：%s"
                           % "、".join(with_id))
    return Plan(proposal, graph, args.kind), graph_path


def cmd_check(args) -> int:
    plan, graph_path = build_plan(args)
    print(render(plan, graph_path.name))
    return 0


def cmd_apply(args) -> int:
    plan, graph_path = build_plan(args)
    engine = resolve_engine(args.engine)
    cmds = engine_commands(plan, args.kind)
    if not cmds:
        print("没有要写的：雏形里的模块与节点都已在 %s 里。" % graph_path.name)
        return 0
    base = ["--graph", str(graph_path), "--kind", args.kind]
    failures = []
    for label, cmd_args in cmds:
        code, out, err = run_engine(engine, base, cmd_args)
        if code == 0:
            print(out or "%s 已写入" % label)
        else:
            failures.append("%s：%s" % (label, err or "引擎退出码 %d" % code))
            print("%s 未写入（见 stderr）" % label)
    if args.kind == "case" and plan.has_time_limits():
        print("时限句没有写进案件图，只在上面的清单里回显过。")
    if failures:
        raise Rejected("引擎拒了 %d 条，其余已写入：\n  " % len(failures) + "\n  ".join(failures))
    return 0


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sketch.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--proposal", required=True, help="雏形文件（JSON），格式见 SKETCH-FORMAT.md")
    common.add_argument("--graph", default=DEFAULT_GRAPH,
                        help="要写的图，默认当前目录的 图.json；预设图给它的 预设图.json 并加 --kind preset")
    common.add_argument("--kind", choices=("case", "preset"), default="case",
                        help="case 案件图（默认）；preset 预设图（收 id 与时限）")

    sub.add_parser("check", parents=[common], help="只读：判同名并回显清单，图一字不动")
    p = sub.add_parser("apply", parents=[common], help="拍板后：经引擎逐条写入")
    p.add_argument("--engine", default=None, help="图引擎 graph.py 的路径，默认取兄弟 skill graph 里的")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "check":
            return cmd_check(args)
        return cmd_apply(args)
    except Rejected as e:
        print("拒绝：%s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
