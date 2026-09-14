#!/usr/bin/env python3
"""雏形 CLI：把模型从指南、指引手册或案件图提出的一批模块与节点，对着一张图判重、回显，拍板后经图引擎写入。

标准库零依赖，不 import 图引擎：写入只经 skill "graph" 的 scripts/graph.py 子进程，它仍是图的唯一写入口。
本脚本不含任何领域语义：判重只看标题，写入只转交引擎。格式与规则见 ../references/雏形格式.md。

用法：
  python sketch.py check     --proposal 雏形.json [--graph 图.json] [--kind case|domain] [--domain 领域图或领域目录]
  python sketch.py apply     --proposal 雏形.json [--graph 图.json] [--kind case|domain] [--domain ...]
                             [--engine graph.py] [--as-new <标题>]...
  python sketch.py from-case --case 案件图.json --domain 领域图或领域目录 [--out 回流.json]
  python sketch.py home      --name <领域名> [--empty] [--live-root <活图根>] [--seed-root <种子根>] [--engine graph.py]
  python sketch.py intake    --name <领域名> [--live-root <活图根>] [--seed-root <种子根>] [--engine graph.py]
  python sketch.py docx-text <文件.docx>

docx-text 把一份 docx（指南、指引手册）的正文按段落打成纯文本，表格一行一行、格间用 | 隔开；模型整读它来提雏形。
check 只读：按标题判重（同名不再提；相似不同名列为待定），回显清单，图一字不动。
apply 拍板后跑：待定未定即拒（--as-new 逐条定为新的，定为同一个的从雏形里删掉），其余逐条交引擎写入，
      引擎的回显照抄；案件图上时限只回显不写（ADR-0016）。
from-case 是回流的第一步（ADR-0012）：从一份案件图里算出「案件图有、领域图没有」且至少一版已确认的模块与节点，
      保留原 id，写成雏形文件；标题的去案件化改写由模型做，再 check / apply --kind domain。
home 回显活图目录的绝对路径（ADR-0019）：活图不在就从 assets/ 下的出厂种子整个拷一份，已经在就一个字不动。
      律师累计在活图上的东西住 skill 包之外，包升级只换种子，碰不到活图。
      --empty 是开发者造一份全新领域时的起点（ADR-0020）：活图不在、包里也没有种子，就在活图位置建目录
      并经引擎起一份空领域图；包里已有种子时拒，不给它盖一份空的。
intake 入库（ADR-0020）：把开发者活图那份 领域图.json 送进本仓库成为出厂种子，只在仓库里跑。
      只拿这一份文件（模板/ 与 指引手册/ 是原件，走普通的 git 添加）；拷之前校验、拷之前把新增与改名分开回显。
      它是一次拷贝，不经图引擎，也不是 skill 包的版本发布；入库要经第二双眼（硬边界 2），那是接下来的 PR。

退出码：0 完成；1 拒绝（雏形不合格式、待定未定、引擎拒写、找不到文件、入库不在仓库里）；2 用法错误。
"""
import argparse
import difflib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from typing import Dict, List, Optional, Tuple

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

DEFAULT_GRAPH = "图.json"
DOMAIN_GRAPH_FILENAME = "领域图.json"
ENGINE_RELATIVE = pathlib.Path("..") / ".." / "graph" / "scripts" / "graph.py"
SEED_ROOT_RELATIVE = pathlib.Path("..") / "assets"      # 出厂种子，随 skill 包分发（ADR-0019）
LIVE_HOME_ENV = "LOO0NG_HOME"                            # 活图的「家」，默认 ~/.loo0ng
LIVE_HOME_DIRNAME = ".loo0ng"
LIVE_DOMAINS_DIRNAME = "领域"
STAGING_SUFFIX = ".拷贝中"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
NO_TEMPLATE = "无"
TEMPLATE_SOURCES = ("官方", "生成")
SIMILAR_RATIO = 0.75  # 归一化后 difflib 相似度阈值；或一方包含另一方。只按标题，不含领域语义。

PROPOSAL_KEYS = {"模块", "来源"}
MODULE_KEYS = {"标题", "节点", "id"}
NODE_KEYS = {"标题", "空白模板", "时限", "id"}

STATUS_NEW, STATUS_EXISTING, STATUS_PENDING, STATUS_BRING = "新", "已在图里", "待定", "领域图带入"


class Rejected(Exception):
    """拒绝：雏形不合格式、待定未定、引擎拒写、找不到文件。图一字不动（引擎拒写的那条除外，其余照写）。"""


# ---------------------------------------------------------------- 标题归一与相似

def normalize(title: str) -> str:
    """判重用的标题：NFKC、小写、去空白与标点符号。"""
    text = unicodedata.normalize("NFKC", title).lower()
    return "".join(c for c in text if not c.isspace() and not unicodedata.category(c).startswith(("P", "S")))


def similar(a: str, b: str) -> bool:
    a, b = normalize(a), normalize(b)
    if not a or not b or a == b:
        return False
    if min(len(a), len(b)) >= 2 and (a in b or b in a):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= SIMILAR_RATIO


def classify(title: str, in_graph: List[str], in_domain: List[str]) -> Tuple[str, Optional[str]]:
    """先对图判：同名 / 相似 / 新；新的再对领域图判同名，同名即「领域图带入」。"""
    status, ref = match(title, in_graph)
    if status == STATUS_NEW and in_domain:
        d_status, d_ref = match(title, in_domain)
        if d_status == STATUS_EXISTING:
            return STATUS_BRING, d_ref
    return status, ref


def match(title: str, existing: List[str]) -> Tuple[str, Optional[str]]:
    """返回 (已在图里 | 待定 | 新, 图里对应的标题)。同名优先于相似；相似取相似度最高的那个。"""
    key = normalize(title)
    for t in existing:
        if normalize(t) == key:
            return STATUS_EXISTING, t
    best, best_ratio = None, 0.0
    for t in existing:
        if similar(title, t):
            ratio = difflib.SequenceMatcher(None, key, normalize(t)).ratio()
            if best is None or ratio > best_ratio:
                best, best_ratio = t, ratio
    if best is not None:
        return STATUS_PENDING, best
    return STATUS_NEW, None


# ---------------------------------------------------------------- 读文件

def read_json(path: pathlib.Path, label: str):
    if not path.is_file():
        raise Rejected("找不到%s：%s" % (label, path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise Rejected("%s 不是合法 JSON：%s" % (label, e)) from e


def resolve_domain_path(arg: Optional[str]) -> Optional[pathlib.Path]:
    if not arg:
        return None
    p = pathlib.Path(arg)
    return p / DOMAIN_GRAPH_FILENAME if p.is_dir() else p


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
    """校验空白模板写法（与引擎 --template 同一套：无 | 官方:<文件名> | 生成:<文件名>），返回原样。"""
    if text == NO_TEMPLATE:
        return text
    if not isinstance(text, str):
        raise Rejected("空白模板写法：无 | 官方:<文件名> | 生成:<文件名>，收到 %r" % (text,))
    source, sep, filename = text.partition(":")
    if not sep or source not in TEMPLATE_SOURCES or not filename.strip():
        raise Rejected("空白模板写法：无 | 官方:<文件名> | 生成:<文件名>（半角冒号），收到 %r" % text)
    return text


def template_text(value: str) -> str:
    if value == NO_TEMPLATE:
        return NO_TEMPLATE
    source, _, filename = value.partition(":")
    return "%s %s" % (source, filename.strip())


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
        raise Rejected("雏形文件顶层键须是 模块（必有）与 来源（可选），实际：%s" % (sorted(data) if isinstance(data, dict) else type(data).__name__))
    if not isinstance(data["模块"], list):
        raise Rejected("雏形文件的 模块 须是数组")
    modules = []
    seen_modules: Dict[str, str] = {}
    seen_nodes: Dict[str, str] = {}
    for m in data["模块"]:
        if not isinstance(m, dict) or not (set(m) <= MODULE_KEYS) or not ({"标题", "节点"} <= set(m)):
            raise Rejected("雏形里每个模块须有 标题 与 节点，可选 id；实际键：%s" % (sorted(m) if isinstance(m, dict) else m))
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
            node = {"标题": nt, "空白模板": parse_template(n["空白模板"]), "id": _check_id(n.get("id"), "节点「%s」" % nt)}
            if "时限" in n:
                if not isinstance(n["时限"], str) or not n["时限"].strip():
                    raise Rejected("节点「%s」的 时限 须是非空字符串" % nt)
                node["时限"] = n["时限"].strip()
            nodes.append(node)
        modules.append({"标题": title, "id": _check_id(m.get("id"), "模块「%s」" % title), "节点": nodes})
    return {"来源": data.get("来源"), "模块": modules}


# ---------------------------------------------------------------- 判重

class Plan:
    """雏形对着一张图判重后的结果：每个模块、节点标上状态与图里对应的标题。"""

    def __init__(self, proposal: dict, graph, domain, kind: str):
        self.kind = kind
        self.source = proposal["来源"]
        g_modules, g_nodes, self.owner = graph_titles(graph)
        d_modules, d_nodes, d_owner = graph_titles(domain) if domain is not None else ([], [], {})
        self.modules: List[dict] = []
        for m in proposal["模块"]:
            item = dict(m, 节点=[])
            item["状态"], item["对应"] = classify(m["标题"], g_modules, d_modules)
            for n in m["节点"]:
                node = dict(n, 备注=None)
                node["状态"], node["对应"] = classify(n["标题"], g_nodes, d_nodes)
                if node["状态"] == STATUS_BRING and normalize(d_owner[node["对应"]]) != normalize(m["标题"]):
                    node["备注"] = "领域图里它属于模块「%s」，放在别的模块下引擎会拒" % d_owner[node["对应"]]
                item["节点"].append(node)
            self.modules.append(item)

    def pending_titles(self) -> List[str]:
        out = [m["标题"] for m in self.modules if m["状态"] == STATUS_PENDING]
        out += [n["标题"] for m in self.modules for n in m["节点"] if n["状态"] == STATUS_PENDING]
        return out

    def resolve_as_new(self, titles: List[str]) -> None:
        pending = set(self.pending_titles())
        for t in titles:
            if t not in pending:
                raise Rejected("--as-new 「%s」不在待定之列（待定：%s）" % (t, "、".join(sorted(pending)) or "无"))
        for m in self.modules:
            if m["状态"] == STATUS_PENDING and m["标题"] in titles:
                m["状态"] = STATUS_NEW
            for n in m["节点"]:
                if n["状态"] == STATUS_PENDING and n["标题"] in titles:
                    n["状态"] = STATUS_NEW

    def doomed(self) -> List[str]:
        """写之前就知道引擎会拒的：与领域图同名却放错模块的节点。"""
        return ["%s：%s" % (n["标题"], n["备注"]) for m in self.modules for n in m["节点"]
                if n["状态"] == STATUS_BRING and n["备注"]]

    def has_time_limits(self) -> bool:
        return any("时限" in n for m in self.modules for n in m["节点"])

    def to_write(self) -> List[Tuple[str, dict, Optional[dict]]]:
        """要交给引擎的条目，按顺序：("module", m, None) 或 ("node", m, n)。已在图里的不写。"""
        items: List[Tuple[str, dict, Optional[dict]]] = []
        for m in self.modules:
            if m["状态"] in (STATUS_NEW, STATUS_BRING):
                items.append(("module", m, None))
            for n in m["节点"]:
                if n["状态"] in (STATUS_NEW, STATUS_BRING):
                    items.append(("node", m, n))
        return items


def render(plan: Plan, graph_name: str) -> str:
    kind_label = "领域图" if plan.kind == "domain" else "案件图"
    lines = ["# 雏形清单（对 %s，%s）" % (graph_name, kind_label), ""]
    if plan.source:
        lines += ["来源：%s" % plan.source, ""]
    new_lines, existing_lines, pending_lines = [], [], []
    for m in plan.modules:
        head = "- 模块「%s」（%s）" % (m["标题"], _module_status_text(m))
        body = []
        for n in m["节点"]:
            if n["状态"] == STATUS_EXISTING:
                existing_lines.append("- 节点「%s」（图里在模块「%s」下）" % (n["标题"], plan.owner.get(n["对应"], "")))
                continue
            if n["状态"] == STATUS_PENDING:
                pending_lines.append("- 节点「%s」与图里的「%s」相似" % (n["标题"], n["对应"]))
            attrs = ["空白模板 %s" % template_text(n["空白模板"])]
            if "时限" in n:
                attrs.append("时限 %s" % n["时限"])
            if n["状态"] == STATUS_BRING:
                attrs.append("领域图有同名，按领域图带入")
            if n["备注"]:
                attrs.append(n["备注"])
            if n["状态"] == STATUS_PENDING:
                attrs.append("待定")
            body.append("  - 节点「%s」：%s" % (n["标题"], "；".join(attrs)))
        if m["状态"] == STATUS_PENDING:
            pending_lines.append("- 模块「%s」与图里的「%s」相似" % (m["标题"], m["对应"]))
        if body or m["状态"] != STATUS_EXISTING:
            new_lines.append(head)
            new_lines.extend(body)
    lines += ["## 新提出", ""]
    lines += new_lines or ["（无）"]
    lines.append("")
    if existing_lines:
        lines += ["## 已在图里，不重复提出", ""] + existing_lines + [""]
    if pending_lines:
        lines += ["## 相似不同名，待定", ""] + pending_lines + [
            "", "是同一个就把它从雏形文件里删掉；不是同一个就在 apply 时加 --as-new <标题>。", ""]
    if plan.kind == "case" and plan.has_time_limits():
        lines += ["时限只回显、案件图不存（ADR-0016）：通用的由开发者回流时写进领域图，本案的具体日期走律师陈述。", ""]
    lines.append("拍板前 %s 一字未动。" % graph_name)
    return "\n".join(lines)


def _module_status_text(m: dict) -> str:
    if m["状态"] == STATUS_EXISTING:
        return "已在图里"
    if m["状态"] == STATUS_BRING:
        return "领域图有同名，按领域图带入"
    if m["状态"] == STATUS_PENDING:
        return "待定：与图里的「%s」相似" % m["对应"]
    return "新"


# ---------------------------------------------------------------- 引擎子进程

def default_engine() -> pathlib.Path:
    return (pathlib.Path(__file__).resolve().parent / ENGINE_RELATIVE).resolve()


def resolve_engine(given: Optional[str]) -> pathlib.Path:
    engine = pathlib.Path(given).resolve() if given else default_engine()
    if not engine.is_file():
        raise Rejected("找不到图引擎 %s；用 --engine 指向 skill \"graph\" 的 scripts/graph.py" % engine)
    return engine


def engine_commands(plan: Plan, kind: str) -> List[Tuple[str, List[str]]]:
    """(条目描述, 引擎子命令参数)。案件图上不传 --id 与 --time-limit：id 由引擎生成，时限只住领域图。"""
    cmds = []
    for what, m, n in plan.to_write():
        if what == "module":
            args = ["add-module", "--title", m["对应"] if m["状态"] == STATUS_BRING else m["标题"]]
            if m["id"]:
                args += ["--id", m["id"]]
            cmds.append(("模块「%s」" % m["标题"], args))
            continue
        module_key = m["对应"] if m["状态"] in (STATUS_EXISTING, STATUS_BRING) else m["标题"]
        title = n["对应"] if n["状态"] == STATUS_BRING else n["标题"]
        args = ["add-node", "--module", module_key, "--title", title, "--template", n["空白模板"]]
        if n["id"]:
            args += ["--id", n["id"]]
        if kind == "domain" and "时限" in n:
            args += ["--time-limit", n["时限"]]
        cmds.append(("节点「%s」" % n["标题"], args))
    return cmds


def run_engine(engine: pathlib.Path, base: List[str], args: List[str]) -> Tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(engine), *base, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ---------------------------------------------------------------- docx 正文

def docx_text(path: pathlib.Path) -> str:
    """正文按段落一行；表格每行一行、格间 |；分节与页眉页脚不取。标准库 zipfile + ElementTree。"""
    if not path.is_file():
        raise Rejected("找不到文件：%s" % path)
    try:
        with zipfile.ZipFile(str(path)) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
        raise Rejected("%s 不是能拆的 docx：%s" % (path.name, e)) from e
    body = root.find(WORD_NS + "body")
    lines: List[str] = []

    def para_text(p) -> str:
        return "".join(t.text or "" for t in p.iter(WORD_NS + "t"))

    def walk(container):
        for child in container:
            if child.tag == WORD_NS + "p":
                lines.append(para_text(child))
            elif child.tag == WORD_NS + "tbl":
                for tr in child.iter(WORD_NS + "tr"):
                    cells = ["".join(para_text(p) for p in tc.iter(WORD_NS + "p")).strip() for tc in tr.findall(WORD_NS + "tc")]
                    lines.append(" | ".join(cells))
            elif child.tag == WORD_NS + "sdt":
                content = child.find(WORD_NS + "sdtContent")
                if content is not None:
                    walk(content)

    if body is not None:
        walk(body)
    out, blank = [], False
    for line in lines:
        if line.strip():
            out.append(line.rstrip())
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out).strip() + "\n"


def cmd_docx_text(args) -> int:
    sys.stdout.write(docx_text(pathlib.Path(args.docx)))
    return 0


# ---------------------------------------------------------------- 三个子命令

def build_plan(args) -> Tuple[Plan, pathlib.Path]:
    graph_path = pathlib.Path(args.graph)
    proposal = load_proposal(pathlib.Path(args.proposal))
    graph = read_json(graph_path, "图")
    domain_path = resolve_domain_path(args.domain)
    domain = read_json(domain_path, "领域图") if domain_path else None
    if args.kind == "case":
        with_id = [x["标题"] for x in proposal["模块"] if x["id"]] + [n["标题"] for x in proposal["模块"] for n in x["节点"] if n["id"]]
        if with_id:
            raise Rejected("案件图里的 id 由引擎生成，雏形里不能给 id（只有 --kind domain 收）：%s" % "、".join(with_id))
    return Plan(proposal, graph, domain, args.kind), graph_path


def cmd_check(args) -> int:
    plan, graph_path = build_plan(args)
    print(render(plan, graph_path.name))
    return 0


def cmd_apply(args) -> int:
    plan, graph_path = build_plan(args)
    plan.resolve_as_new(args.as_new or [])
    pending = plan.pending_titles()
    if pending:
        raise Rejected("待定未定，一字不写：%s。是同一个就从雏形文件里删掉，不是就加 --as-new <标题>" % "、".join(pending))
    doomed = plan.doomed()
    if doomed:
        raise Rejected("有节点放错了模块，一字不写：%s。改雏形里的模块归属，或带入后用引擎 move-node 移动" % "；".join(doomed))
    engine = resolve_engine(args.engine)
    cmds = engine_commands(plan, args.kind)
    if not cmds:
        print("没有要写的：雏形里的模块与节点都已在 %s 里。" % graph_path.name)
        return 0
    base = ["--graph", str(graph_path), "--kind", args.kind]
    if args.domain:
        base += ["--domain", args.domain]
    failures = []
    for label, cmd_args in cmds:
        code, out, err = run_engine(engine, base, cmd_args)
        if code == 0:
            print(out or "%s 已写入" % label)
        else:
            failures.append("%s：%s" % (label, err or "引擎退出码 %d" % code))
            print("%s 未写入（见 stderr）" % label)
    if args.kind == "case" and plan.has_time_limits():
        print("时限句没有写进案件图（ADR-0016），只在上面的清单里回显过。")
    if failures:
        raise Rejected("引擎拒了 %d 条，其余已写入：\n  " % len(failures) + "\n  ".join(failures))
    return 0


def used_once(entries: List[dict]) -> bool:
    """ADR-0012 判据 (a)：至少一版已确认，且现在不是不适用（末条不适用即终态，不是候选）。"""
    return any(e.get("动作") == "确认" for e in entries) and (not entries or entries[-1].get("动作") != "不适用")


def cmd_from_case(args) -> int:
    case_path = pathlib.Path(args.case)
    case = read_json(case_path, "案件图")
    domain_path = resolve_domain_path(args.domain)
    domain = read_json(domain_path, "领域图")
    if not isinstance(case.get("模块"), list) or not isinstance(domain.get("模块"), list):
        raise Rejected("案件图与领域图的顶层都须有 模块 数组")
    if case.get("领域") != domain.get("领域"):
        raise Rejected("只回本领域的图（ADR-0012）：案件图领域「%s」，领域图领域「%s」" % (case.get("领域"), domain.get("领域")))
    domain_ids = {m["id"] for m in domain["模块"]} | {n["id"] for m in domain["模块"] for n in m["节点"]}
    domain_module_title = {m["id"]: m["标题"] for m in domain["模块"]}
    modules = []
    for m in case["模块"]:
        nodes = []
        for n in m["节点"]:
            if n["id"] in domain_ids or not used_once(n.get("条目", [])):
                continue
            tpl = n["空白模板"]
            node = {"标题": n["标题"], "id": n["id"],
                    "空白模板": "官方:%s" % tpl["文件"] if isinstance(tpl, dict) and tpl.get("来源") == "官方" else NO_TEMPLATE}
            nodes.append(node)
        if not nodes:
            continue
        if m["id"] in domain_ids:
            modules.append({"标题": domain_module_title[m["id"]], "id": m["id"], "节点": nodes})
        else:
            modules.append({"标题": m["标题"], "id": m["id"], "节点": nodes})
    if not modules:
        print("没有回流候选：案件图里没有「领域图没有、且至少一版已确认」的节点。")
        return 0
    proposal = {"来源": "案件图 %s（回流）" % case_path.name, "模块": modules}
    text = json.dumps(proposal, ensure_ascii=False, indent=2) + "\n"
    out_path = pathlib.Path(args.out) if args.out else None
    if out_path is not None:
        # 显式 open：Path.write_text 的 newline= 是 3.10 才有的（#61）
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("回流候选（保留案件里的 id；标题须去案件化后再 check / apply --kind domain）：")
    for m in modules:
        print("- 模块「%s」（%s）" % (m["标题"], "领域图已有" if m["id"] in domain_ids else "新"))
        for n in m["节点"]:
            print("  - 节点「%s」：空白模板 %s；id %s" % (n["标题"], template_text(n["空白模板"]), n["id"]))
    if out_path is not None:
        print("已写 %s" % out_path)
    else:
        print(text, end="")
    return 0


# ---------------------------------------------------------------- home（活图，ADR-0019）

def live_root(given: Optional[str] = None) -> pathlib.Path:
    """活图根：默认 ~/.loo0ng/领域/。环境变量 LOO0NG_HOME 换的是那个「家」（`.loo0ng` 那一层），
    脚本层单测与 eval 用它把活图挪进临时目录（ADR-0015 只生不存），律师那台机上不设。"""
    if given:
        return pathlib.Path(given).resolve()
    home = os.environ.get(LIVE_HOME_ENV, "").strip()
    base = pathlib.Path(home) if home else pathlib.Path.home() / LIVE_HOME_DIRNAME
    return (base / LIVE_DOMAINS_DIRNAME).resolve()


def seed_root(given: Optional[str] = None) -> pathlib.Path:
    """出厂种子根：本 skill 的 assets/，随包分发，升级时整个被换掉。"""
    if given:
        return pathlib.Path(given).resolve()
    return (pathlib.Path(__file__).resolve().parent / SEED_ROOT_RELATIVE).resolve()


def copy_seed(seed: pathlib.Path, live: pathlib.Path) -> int:
    """整份拷过去：先落在同级的临时名上，拷完再改名。拷到一半断了不会留下半份活图，
    否则下一次起手会把那半份当成「已有活图」再也不补。回件数。"""
    live.parent.mkdir(parents=True, exist_ok=True)
    staging = live.parent / ("%s%s-%d" % (live.name, STAGING_SUFFIX, os.getpid()))
    if staging.exists():
        shutil.rmtree(staging)
    try:
        shutil.copytree(str(seed), str(staging))
        os.replace(str(staging), str(live))
    except OSError as e:
        shutil.rmtree(staging, ignore_errors=True)
        raise Rejected("拷不动出厂种子 %s：%s。活图没建，一个字没写。" % (seed.as_posix(), e)) from e
    return sum(1 for x in live.rglob("*") if x.is_file())


def check_domain_name(name: str) -> str:
    if name in ("", ".", "..") or "/" in name or "\\" in name or ":" in name:
        raise Rejected("领域名是一个目录名，不能带路径分隔符，收到 %r" % name)
    return name


def init_empty(name: str, live: pathlib.Path, engine: pathlib.Path) -> str:
    """在活图位置建目录，经引擎起一份空领域图（ADR-0020）：开发者造一份全新领域的种子从这里起步。

    写图仍只经引擎子进程，本脚本不自己拼 JSON。与 copy_seed 一个形状：先落在同级的临时名上，
    起完再改名，起到一半断了不会留下半份活图被下一次当成「已有活图」。回引擎那行原话。
    """
    live.parent.mkdir(parents=True, exist_ok=True)
    staging = live.parent / ("%s%s-%d" % (live.name, STAGING_SUFFIX, os.getpid()))
    shutil.rmtree(staging, ignore_errors=True)
    try:
        staging.mkdir(parents=True)
        code, out, err = run_engine(engine, ["--graph", str(staging / DOMAIN_GRAPH_FILENAME), "--kind", "domain"],
                                    ["init", "--empty", "--name", name])
        if code != 0:
            raise Rejected("引擎拒了空领域图，活图没建、一个字没写：%s" % (err or out or "引擎退出码 %d" % code))
        os.replace(str(staging), str(live))
    except OSError as e:
        raise Rejected("建不出活图 %s：%s。一个字没写。" % (live.as_posix(), e)) from e
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return out


def cmd_home(args) -> int:
    name = check_domain_name(args.name)
    live = live_root(args.live_root) / name
    seed = seed_root(args.seed_root) / name
    if live.is_dir():
        print("活图：%s" % live.as_posix())
        print("已有活图，一个字没动：律师在这个领域上累计的东西只住这里，skill 包升级只换出厂种子。")
        return 0
    if live.exists():
        raise Rejected("%s 已经存在但不是目录：活图位置被占了，挪开它再起手。" % live.as_posix())
    if args.empty:
        if seed.is_dir():
            raise Rejected("领域「%s」包里已经有出厂种子 %s：--empty 只给还没有种子的新领域用，"
                           "不带 --empty 再跑一次就从种子整份拷一份过去。" % (name, seed.as_posix()))
        note = init_empty(name, live, resolve_engine(args.engine))
        print("活图：%s" % live.as_posix())
        print("新领域从空图起手：活图位置上没有这个领域、包里也没有出厂种子，已在活图位置建了目录并起一份空领域图。")
        if note:
            print(note)
        print("官方模板原件与指引手册原文自己放进 %s 下的 模板/ 与 指引手册/（ADR-0004）；"
              "模块与节点办一遍案子回流进来（本 skill 正文「回流」），攒够了再 intake 入库成出厂种子。"
              % live.as_posix())
        return 0
    if not seed.is_dir():
        raise Rejected("既没有活图 %s，也没有出厂种子 %s：律师侧的新领域从空图起手（skill \"setup-case\" 的 "
                       "init --empty --name %s，不给 --domain），领域目录等它有内容了再建；"
                       "开发侧要造这个领域的领域图，加 --empty 再跑一次，它在活图位置建目录并起一份空领域图。"
                       % (live.as_posix(), seed.as_posix(), name))
    count = copy_seed(seed, live)
    print("活图：%s" % live.as_posix())
    print("首次起手：活图位置上还没有这个领域，已从出厂种子 %s 整份拷了 %d 件过去。"
          % (seed.as_posix(), count))
    print("往后只认活图：律师改的写在这里，skill 包升级只换种子，碰不到它。")
    return 0


# ---------------------------------------------------------------- intake（入库，ADR-0020）

def in_repo(path: pathlib.Path) -> bool:
    """祖先里有 .git。只用来判入库的落点在不在一个工作树里，与引擎那条「包内种子谁都不许写」
    无关：ADR-0020 拒的是拿 .git 去认「这是不是开发会话」（会误伤把活图放进 git 备份的律师），
    这里判的是被写的那一份种子在不在仓库里，方向相反。"""
    for d in [path] + list(path.parents):
        if (d / ".git").exists():
            return True
    return False


def graph_template_text(value) -> str:
    if isinstance(value, dict):
        return "%s %s" % (value.get("来源"), value.get("文件"))
    return NO_TEMPLATE


def index_domain(data) -> Tuple[Dict[str, dict], Dict[str, Tuple[dict, dict]]]:
    """(id -> 模块, id -> (所在模块, 节点))。入库的 diff 按 id 比，标题改了也认得出是同一个。"""
    modules: Dict[str, dict] = {}
    nodes: Dict[str, Tuple[dict, dict]] = {}
    for m in data.get("模块", []):
        modules[m["id"]] = m
        for n in m.get("节点", []):
            nodes[n["id"]] = (m, n)
    return modules, nodes


def diff_domain(seed, live) -> Dict[str, List[str]]:
    """活图这份领域图比种子多了/改了什么。新增、改名、改属性、改归属、种子里有而活图里没有，各一栏。

    分栏是本条的重点（ADR-0020）：开发者的活图里混着他试办案子回流进去的东西，入库是整份送进去，
    第二双眼与隐私钩子之前，这几行是第一道人眼过滤。
    """
    s_modules, s_nodes = index_domain(seed) if seed is not None else ({}, {})
    l_modules, l_nodes = index_domain(live)
    out = {"新增模块": [], "新增节点": [], "改名": [], "改属性": [], "改归属": [], "只在种子里": []}
    for mid, m in l_modules.items():
        if mid not in s_modules:
            out["新增模块"].append("模块「%s」（id %s，%d 个节点）" % (m["标题"], mid, len(m.get("节点", []))))
        elif s_modules[mid]["标题"] != m["标题"]:
            out["改名"].append("模块 %s：「%s」→「%s」" % (mid, s_modules[mid]["标题"], m["标题"]))
    for nid, (owner, n) in l_nodes.items():
        if nid not in s_nodes:
            out["新增节点"].append("节点「%s」（模块「%s」，id %s，空白模板 %s%s）" % (
                n["标题"], owner["标题"], nid, graph_template_text(n["空白模板"]),
                "，有时限句" if n.get("时限") else ""))
            continue
        s_owner, s_node = s_nodes[nid]
        if s_node["标题"] != n["标题"]:
            out["改名"].append("节点 %s：「%s」→「%s」" % (nid, s_node["标题"], n["标题"]))
        if s_node["空白模板"] != n["空白模板"]:
            out["改属性"].append("节点 %s「%s」：空白模板 %s → %s" % (
                nid, n["标题"], graph_template_text(s_node["空白模板"]), graph_template_text(n["空白模板"])))
        if s_node.get("时限") != n.get("时限"):
            out["改属性"].append("节点 %s「%s」：时限 %s → %s" % (
                nid, n["标题"], s_node.get("时限") or "（无）", n.get("时限") or "（无）"))
        if s_owner["id"] != owner["id"]:
            out["改归属"].append("节点 %s「%s」：模块「%s」→「%s」" % (
                nid, n["标题"], s_owner["标题"], owner["标题"]))
    for mid, m in s_modules.items():
        if mid not in l_modules:
            out["只在种子里"].append("模块 %s「%s」" % (mid, m["标题"]))
    for nid, (_, n) in s_nodes.items():
        if nid not in l_nodes:
            out["只在种子里"].append("节点 %s「%s」" % (nid, n["标题"]))
    return out


def cmd_intake(args) -> int:
    name = check_domain_name(args.name)
    live_dir = live_root(args.live_root) / name
    live_graph = live_dir / DOMAIN_GRAPH_FILENAME
    seeds = seed_root(args.seed_root)
    seed_dir = seeds / name
    seed_graph = seed_dir / DOMAIN_GRAPH_FILENAME
    if not in_repo(seeds):
        raise Rejected("入库只在本仓库里做（ADR-0020）：种子根 %s 的祖先里没有 .git，"
                       "你手上这份是装好的 skill 包，写进去下一次升级就被整个换掉。"
                       "克隆仓库、在仓库里的 skills/in-progress/domain/scripts/sketch.py 上跑这一条。" % seeds.as_posix())
    if not live_graph.is_file():
        raise Rejected("找不到活图那份领域图 %s：入库的起点是开发者自己的活图（先 home，"
                       "新领域用 home --empty）。" % live_graph.as_posix())
    code, out, err = run_engine(resolve_engine(args.engine),
                                ["--graph", str(live_graph), "--kind", "domain"], ["validate"])
    if code != 0:
        raise Rejected("活图那份领域图不合校验，一个字没拷：%s" % (err or out or "引擎退出码 %d" % code))
    live = read_json(live_graph, "活图的领域图")
    if live.get("领域") != name:
        raise Rejected("活图那份领域图里写的领域是「%s」，与 --name %s 对不上：入库会把它放进种子的 %s/ 下，"
                       "两边对不上说明拿错了目录。" % (live.get("领域"), name, name))
    seed = read_json(seed_graph, "出厂种子") if seed_graph.is_file() else None
    print("入库：领域「%s」" % name)
    print("  活图 %s" % live_graph.as_posix())
    print("  种子 %s%s" % (seed_graph.as_posix(), "" if seed is not None else "（仓库里还没有，这是第一次入库）"))
    d = diff_domain(seed, live)
    print("这次比种子多了 %d 个模块、%d 个节点，改了 %d 个标题、%d 处属性、%d 处归属；种子里有而活图里没有的 %d 个。"
          % (len(d["新增模块"]), len(d["新增节点"]), len(d["改名"]), len(d["改属性"]),
             len(d["改归属"]), len(d["只在种子里"])))
    for 栏 in ("新增模块", "新增节点", "改名", "改属性", "改归属", "只在种子里"):
        if d[栏]:
            print("%s（%d）：" % ("种子里有、活图里没有" if 栏 == "只在种子里" else 栏, len(d[栏])))
            for line in d[栏]:
                print("- %s" % line)
    if d["只在种子里"]:
        print("上面这几个入库之后种子里就没有了：入库是整份换掉，不是两份合并。要留着它们，先在活图上补回来再入库。")
    if seed_graph.is_file() and seed_graph.read_bytes() == live_graph.read_bytes():
        print("与种子逐字相同，一个字没拷：没有要入库的。")
        return 0
    seed_dir.mkdir(parents=True, exist_ok=True)
    tmp = seed_graph.with_name(seed_graph.name + STAGING_SUFFIX)
    try:
        shutil.copyfile(str(live_graph), str(tmp))
        os.replace(str(tmp), str(seed_graph))
    except OSError as e:
        if tmp.exists():
            tmp.unlink()
        raise Rejected("拷不进种子 %s：%s。种子一个字没改。" % (seed_graph.as_posix(), e)) from e
    print("已入库：%s。只这一份 %s；%s 下的 模板/ 与 指引手册/ 一个字没动，"
          "官方模板原件与指引手册原文是原件，走普通的 git 添加。" % (seed_graph.as_posix(), DOMAIN_GRAPH_FILENAME, seed_dir.as_posix()))
    print("入库不是 skill 包的版本发布（ADR-0009「维护即发布」说的是另一件事，一次包发布可以带零次或多次入库）："
          "这一条只把文件放进工作树，接着走分支、commit、PR，第二双眼审的就是上面这段 diff（硬边界 2），"
          "隐私钩子在 main 上守着（ADR-0014）。")
    print("它是一次拷贝，不经图引擎：引擎那条「包内出厂种子谁都不许写」照旧管着会话里的每一次写图（ADR-0020），"
          "入库没有绕过它，只是走的另一条路：一次要人审的 git 提交。")
    return 0


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sketch.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--proposal", required=True, help="雏形文件（JSON），格式见 references/雏形格式.md")
    common.add_argument("--graph", default=DEFAULT_GRAPH, help="要写的图，默认当前目录的 图.json；领域图给 领域图.json 并加 --kind domain")
    common.add_argument("--kind", choices=("case", "domain"), default="case", help="case 案件图（默认）；domain 领域图")
    common.add_argument("--domain", default=None, help="领域图 JSON 或领域目录；案件图有它才能按领域图带入同名节点")

    sub.add_parser("check", parents=[common], help="只读：判重并回显清单，图一字不动")
    p = sub.add_parser("apply", parents=[common], help="拍板后：经引擎逐条写入；待定未定即拒")
    p.add_argument("--engine", default=None, help="图引擎 graph.py 的路径，默认取兄弟 skill graph 里的")
    p.add_argument("--as-new", action="append", default=[], help="把这个待定标题定为新的（可重复）；定为同一个的从雏形里删掉")

    p = sub.add_parser("from-case", help="回流第一步：从案件图算出候选，写成雏形文件（保留 id）")
    p.add_argument("--case", required=True, help="案件工作区里的 图.json（只读）")
    p.add_argument("--domain", required=True, help="领域图 JSON 或领域目录")
    p.add_argument("--out", default=None, help="雏形文件落点；不给就打到标准输出")

    p = sub.add_parser("home", help="回显活图目录的绝对路径；没有就从出厂种子拷一份，有就一个字不动")
    p.add_argument("--name", required=True, help="领域名，如 破产；它就是活图下的目录名")
    p.add_argument("--empty", action="store_true",
                   help="开发侧造新领域：活图与出厂种子都没有时，建目录并起一份空领域图；包里有种子即拒")
    p.add_argument("--live-root", default=None,
                   help="活图根，默认 ~/.loo0ng/领域（环境变量 %s 换「家」）" % LIVE_HOME_ENV)
    p.add_argument("--seed-root", default=None, help="出厂种子根，默认本 skill 的 assets/")
    p.add_argument("--engine", default=None, help="图引擎 graph.py 的路径，默认取兄弟 skill graph 里的；只有 --empty 用它")

    p = sub.add_parser("intake", help="入库：把活图那份 领域图.json 送进本仓库成为出厂种子；拷之前校验并回显 diff")
    p.add_argument("--name", required=True, help="领域名；活图与种子两边的目录名")
    p.add_argument("--live-root", default=None,
                   help="活图根，默认 ~/.loo0ng/领域（环境变量 %s 换「家」）" % LIVE_HOME_ENV)
    p.add_argument("--seed-root", default=None, help="出厂种子根，默认本 skill 的 assets/；须在一个 git 工作树里")
    p.add_argument("--engine", default=None, help="图引擎 graph.py 的路径，默认取兄弟 skill graph 里的；拷之前用它校验")

    p = sub.add_parser("docx-text", help="把一份 docx 的正文打成纯文本（段落一行、表格一行一行）")
    p.add_argument("docx", help="指南或指引手册的 .docx")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "check":
            return cmd_check(args)
        if args.cmd == "apply":
            return cmd_apply(args)
        if args.cmd == "home":
            return cmd_home(args)
        if args.cmd == "intake":
            return cmd_intake(args)
        if args.cmd == "docx-text":
            return cmd_docx_text(args)
        return cmd_from_case(args)
    except Rejected as e:
        print("拒绝：%s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
