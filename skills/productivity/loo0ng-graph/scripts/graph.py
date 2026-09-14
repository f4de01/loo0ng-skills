#!/usr/bin/env python3
"""图引擎 CLI：案件图与领域图的唯一写入缝。标准库零依赖，Windows 中文路径可用。

图是工作区根的单一 JSON 图.json（ADR-0003）：顶层只有 格式版本、领域、模块；模块内嵌节点，节点内嵌条目。
条目只追加（生成 / 确认 / 不适用），状态只算不存；每次写图后覆盖重算 图视图.md 与 图视图.json（ADR-0011）。
字段表与最小样例见 ../references/格式.md。

用法：
  python graph.py [--graph 图.json] [--domain 领域图.json 或领域目录] [--kind case|domain] <子命令> ...

子命令（--help 看各自参数）：
  init            起手：--empty | --full | --from 路径
  validate        只校验不写
  views           只重算两份视图
  add-module / rename-module / move-module / delete-module
  add-node / rename-node / move-node / set-template / set-time-limit
  generate / confirm / not-applicable

退出码：0 落盘；1 拒绝（规则或文件不合校验，文件一字不动）；2 用法错误。
"""
import argparse
import datetime as _dt
import json
import os
import pathlib
import re
import secrets
import sys
from typing import Dict, List, Optional, Tuple

FORMAT_VERSION = 1  # 图.json 与 图视图.json 共用，同步升（ADR-0011）
DEFAULT_GRAPH = "图.json"
DOMAIN_GRAPH_FILENAME = "领域图.json"
# 包内出厂种子的判据（ADR-0020）。同一套判据在 skill "loo0ng-setup-case" 的 setup.py 里也有一份
# （那边只报不拒，是起手给错 --domain 时的提示）：改这三个常量或下面 in_package 的判法，要改另一处。
SEED_ASSETS_DIRNAME = "assets"
SEED_SKILL_DIRNAME = "loo0ng-domain"
SEED_ROOT_RELATIVE = pathlib.Path("..") / ".." / SEED_SKILL_DIRNAME / SEED_ASSETS_DIRNAME
VIEW_MD = "图视图.md"
VIEW_JSON = "图视图.json"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

NO_TEMPLATE = "无"
TEMPLATE_SOURCES = ("官方", "生成")
ACTIONS = ("生成", "确认", "不适用")
SOURCE_AGENT, SOURCE_LAWYER = "agent", "律师"
ORIGIN_DOMAIN, ORIGIN_CASE = "领域图", "案件"
STATE_NONE, STATE_GENERATED, STATE_CONFIRMED, STATE_NA = "未生成", "已生成", "已确认", "不适用"
STATE_AHEAD = "尚未进图"
MODULE_IN_GRAPH = "已进图"  # 前方里模块已在图内、只有部分节点没进图
MODULE_NA, MODULE_DONE, MODULE_ACTIVE = "不适用", "已完成", "进行中"

GRAPH_KEYS = {"格式版本", "领域", "模块"}
MODULE_KEYS = {"id", "标题", "节点"}
NODE_KEYS = {"id", "标题", "空白模板", "条目"}
NODE_OPTIONAL_DOMAIN = {"时限"}
ENTRY_KEYS = {
    "生成": ({"动作", "时间", "来源", "文书", "审查报告"}, {"源"}),
    "确认": ({"动作", "时间", "来源", "原话"}, set()),
    "不适用": ({"动作", "时间", "来源", "原话"}, set()),
}


class Rejected(Exception):
    """引擎拒写：规则不允许，或文件不合校验。文件一字不动。"""


class Position:
    """排序目标：--before/--after 某兄弟，或 --first/--last。一个都没给时 empty 为真。"""

    def __init__(self, before=None, after=None, first=False, last=False):
        given = [x for x in (before, after, first, last) if x]
        if len(given) > 1:
            raise Rejected("排序只能给 --before、--after、--first、--last 之一")
        self.before, self.after, self.first, self.last = before, after, first, last
        self.empty = not given

    @classmethod
    def from_args(cls, args):
        return cls(getattr(args, "before", None), getattr(args, "after", None),
                   getattr(args, "first", False), getattr(args, "last", False))


class Invalid(Rejected):
    pass


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return "%s-%s" % (prefix, secrets.token_hex(4))


# ---------------------------------------------------------------- 校验

def _check(cond, msg):
    if not cond:
        raise Invalid(msg)


def validate_graph(data, *, kind: str, label: str) -> None:
    """kind 是 case 或 domain。案件图节点不得带 时限；领域图不得有条目。"""
    _check(isinstance(data, dict), "%s 顶层须是对象" % label)
    _check(set(data) == GRAPH_KEYS, "%s 顶层键须恰为 格式版本、领域、模块，实际：%s" % (label, "、".join(sorted(data))))
    _check(data["格式版本"] == FORMAT_VERSION and isinstance(data["格式版本"], int) and not isinstance(data["格式版本"], bool),
           "%s 的格式版本是 %r，本引擎只认 %d" % (label, data["格式版本"], FORMAT_VERSION))
    _check(isinstance(data["领域"], str), "%s 的 领域 须是字符串" % label)
    _check(isinstance(data["模块"], list), "%s 的 模块 须是数组" % label)
    ids, module_titles, node_titles = set(), set(), set()
    for m in data["模块"]:
        _check(isinstance(m, dict) and set(m) == MODULE_KEYS, "%s 里模块的键须恰为 id、标题、节点" % label)
        _check(isinstance(m["id"], str) and ID_RE.match(m["id"]), "%s 里模块 id %r 不合法" % (label, m["id"]))
        _check(m["id"] not in ids, "%s 里 id %s 重复" % (label, m["id"]))
        ids.add(m["id"])
        _check(isinstance(m["标题"], str) and m["标题"].strip(), "%s 里模块 %s 标题为空" % (label, m["id"]))
        _check(m["标题"] not in module_titles, "%s 里模块标题「%s」重复" % (label, m["标题"]))
        module_titles.add(m["标题"])
        _check(isinstance(m["节点"], list), "%s 里模块「%s」的 节点 须是数组" % (label, m["标题"]))
        for n in m["节点"]:
            _check(isinstance(n, dict), "%s 里节点须是对象" % label)
            allowed = NODE_KEYS | (NODE_OPTIONAL_DOMAIN if kind == "domain" else set())
            extra = set(n) - allowed
            missing = NODE_KEYS - set(n)
            _check(not missing, "%s 里节点缺键：%s" % (label, "、".join(sorted(missing))))
            if extra == {"时限"} and kind == "case":
                raise Invalid("%s 是案件图，节点「%s」不得带 时限（时限只住领域图，ADR-0016）" % (label, n.get("标题")))
            _check(not extra, "%s 里节点「%s」有未知键：%s" % (label, n.get("标题"), "、".join(sorted(extra))))
            _check(isinstance(n["id"], str) and ID_RE.match(n["id"]), "%s 里节点 id %r 不合法" % (label, n["id"]))
            _check(n["id"] not in ids, "%s 里 id %s 重复" % (label, n["id"]))
            ids.add(n["id"])
            _check(isinstance(n["标题"], str) and n["标题"].strip(), "%s 里节点 %s 标题为空" % (label, n["id"]))
            _check(n["标题"] not in node_titles, "%s 里节点标题「%s」重复" % (label, n["标题"]))
            node_titles.add(n["标题"])
            validate_template(n["空白模板"], label, n["标题"])
            if "时限" in n:
                _check(isinstance(n["时限"], str) and n["时限"].strip(), "%s 里节点「%s」的 时限 须是非空字符串" % (label, n["标题"]))
            _check(isinstance(n["条目"], list), "%s 里节点「%s」的 条目 须是数组" % (label, n["标题"]))
            if kind == "domain":
                _check(not n["条目"], "%s 是领域图，节点「%s」不得有条目" % (label, n["标题"]))
            validate_entries(n["条目"], label, n["标题"])


def is_relative_path(text: str) -> bool:
    """相对工作区根、正斜杠、不向上越界。Windows 上 os.path.isabs 不认无盘符的 /x，所以另查开头。"""
    return not (os.path.isabs(text) or text.startswith("/") or "\\" in text or text.startswith("../")
                or text == ".." or "/../" in text or (len(text) > 1 and text[1] == ":"))


def validate_template(value, label, title):
    if value == NO_TEMPLATE:
        return
    _check(isinstance(value, dict) and set(value) == {"来源", "文件"},
           "%s 里节点「%s」的 空白模板 须是「无」或 {来源, 文件}" % (label, title))
    _check(value["来源"] in TEMPLATE_SOURCES, "%s 里节点「%s」的空白模板来源须是 官方 或 生成" % (label, title))
    _check(isinstance(value["文件"], str) and value["文件"].strip(), "%s 里节点「%s」的空白模板文件为空" % (label, title))


def validate_entries(entries, label, title):
    state = STATE_NONE
    for e in entries:
        _check(isinstance(e, dict) and e.get("动作") in ACTIONS, "%s 里节点「%s」有条目的 动作 不合法" % (label, title))
        required, optional = ENTRY_KEYS[e["动作"]]
        _check(required <= set(e) <= required | optional,
               "%s 里节点「%s」的 %s 条目键不对：%s" % (label, title, e["动作"], "、".join(sorted(e))))
        for k in set(e) - {"动作"}:
            _check(isinstance(e[k], str) and e[k], "%s 里节点「%s」条目的 %s 须是非空字符串" % (label, title, k))
        for k in ("文书", "源", "审查报告"):
            if k in e:
                _check(is_relative_path(e[k]), "%s 里节点「%s」条目的 %s 须是相对工作区根的正斜杠路径：%r" % (label, title, k, e[k]))
        if e["动作"] == "生成":
            _check(e["来源"] in (SOURCE_AGENT, SOURCE_LAWYER), "%s 里节点「%s」生成条目的来源不合法" % (label, title))
            _check(state != STATE_NA, "%s 里节点「%s」在不适用之后又有生成条目" % (label, title))
            state = STATE_GENERATED
        else:
            _check(e["来源"] == SOURCE_LAWYER, "%s 里节点「%s」的 %s 条目来源须是律师" % (label, title, e["动作"]))
            if e["动作"] == "确认":
                _check(state == STATE_GENERATED, "%s 里节点「%s」的确认条目前面不是生成" % (label, title))
                state = STATE_CONFIRMED
            else:
                _check(state in (STATE_NONE, STATE_GENERATED), "%s 里节点「%s」在 %s 之后又记不适用" % (label, title, state))
                state = STATE_NA


# ---------------------------------------------------------------- 状态推算（规则住引擎）

def node_state(node) -> str:
    entries = node["条目"]
    if not entries:
        return STATE_NONE
    return {"生成": STATE_GENERATED, "确认": STATE_CONFIRMED, "不适用": STATE_NA}[entries[-1]["动作"]]


def module_state(module) -> str:
    states = [node_state(n) for n in module["节点"]]
    if states and all(s == STATE_NA for s in states):
        return MODULE_NA
    if states and all(s in (STATE_CONFIRMED, STATE_NA) for s in states):
        return MODULE_DONE
    return MODULE_ACTIVE


def versions(node) -> List[dict]:
    out = []
    for e in node["条目"]:
        if e["动作"] == "生成":
            v = {"版本": len(out) + 1, "文书": e["文书"]}
            if "源" in e:
                v["源"] = e["源"]
            v["审查报告"] = e["审查报告"]
            v["时间"] = e["时间"]
            v["来源"] = e["来源"]
            out.append(v)
    return out


# ---------------------------------------------------------------- 读写

def read_json(path: pathlib.Path, label: str):
    if not path.is_file():
        raise Rejected("找不到 %s：%s" % (label, path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise Invalid("%s 不是合法 JSON：%s" % (label, e)) from e


def write_json_atomic(path: pathlib.Path, obj) -> None:
    """临时文件 + os.replace，单写者不设锁（ADR-0003）。"""
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    write_text_atomic(path, text)


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
    try:
        # 显式 open：Path.write_text 的 newline= 是 3.10 才有的，律师那台 mac 是 3.9（#61）
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def in_package(graph_path: pathlib.Path) -> bool:
    """这份领域图是不是包内的出厂种子。两条判据取或：兄弟 skill 的 assets/ 下（按本脚本的位置算，
    装在哪儿都成立），或者目录名摆成 <...>/loo0ng-domain/assets/<领域名>（别处拷来的一份包）。"""
    d = graph_path.resolve().parent
    sibling = (pathlib.Path(__file__).resolve().parent / SEED_ROOT_RELATIVE).resolve()
    try:
        d.relative_to(sibling)
        return True
    except ValueError:
        pass
    return (d.parent.name == SEED_ASSETS_DIRNAME
            and d.parent.parent.name == SEED_SKILL_DIRNAME)


def resolve_domain_path(arg: Optional[str]) -> Optional[pathlib.Path]:
    if not arg:
        return None
    p = pathlib.Path(arg)
    return p / DOMAIN_GRAPH_FILENAME if p.is_dir() else p


def load_domain(path: Optional[pathlib.Path]):
    if path is None:
        return None
    data = read_json(path, "领域图")
    try:
        validate_graph(data, kind="domain", label="领域图 %s" % path.name)
    except Invalid as e:
        raise Rejected("领域图不合校验：%s；领域图归开发会话维护，案件图一字未动" % e) from e
    return data


# ---------------------------------------------------------------- 查找

def find_module(data, key: str):
    for m in data["模块"]:
        if m["id"] == key or m["标题"] == key:
            return m
    return None


def find_node(data, key: str) -> Tuple[Optional[dict], Optional[dict]]:
    for m in data["模块"]:
        for n in m["节点"]:
            if n["id"] == key or n["标题"] == key:
                return m, n
    return None, None


def all_ids(data) -> set:
    ids = set()
    for m in data["模块"]:
        ids.add(m["id"])
        ids.update(n["id"] for n in m["节点"])
    return ids


def module_titles(data) -> set:
    return {m["标题"] for m in data["模块"]}


def node_titles(data) -> set:
    return {n["标题"] for m in data["模块"] for n in m["节点"]}


def domain_order(domain) -> Dict[str, int]:
    """领域图里每个模块与节点的序号（模块按模块序，节点按模块内序）。"""
    order = {}
    for i, m in enumerate(domain["模块"]):
        order[m["id"]] = i
        for j, n in enumerate(m["节点"]):
            order[n["id"]] = j
    return order


def insert_by_domain_order(siblings: List[dict], item: dict, order: Dict[str, int]) -> None:
    """按领域图相对顺序插进已有兄弟之间：放在领域序更小的最后一个领域兄弟之后；
    没有就放在领域序更大的第一个领域兄弟之前；都没有就追加。律师自加的兄弟位置不动。"""
    mine = order[item["id"]]
    last_smaller = None
    first_larger = None
    for idx, s in enumerate(siblings):
        if s["id"] not in order:
            continue
        if order[s["id"]] < mine:
            last_smaller = idx
        elif first_larger is None:
            first_larger = idx
    if last_smaller is not None:
        siblings.insert(last_smaller + 1, item)
    elif first_larger is not None:
        siblings.insert(first_larger, item)
    else:
        siblings.append(item)


def strip_for_case(node: dict) -> dict:
    """从领域图带入案件图：只带 id、标题、空白模板；时限不拷贝（ADR-0016），条目为空。"""
    return {"id": node["id"], "标题": node["标题"], "空白模板": node["空白模板"], "条目": []}


# ---------------------------------------------------------------- 引擎

class Engine:
    def __init__(self, graph_path: pathlib.Path, domain_path: Optional[pathlib.Path], kind: str):
        self.graph_path = graph_path
        self.domain_path = domain_path
        self.kind = kind
        self.domain = load_domain(domain_path) if kind == "case" else None
        self.data = None
        self.notes: List[str] = []  # 回显

    # ---- 生命周期
    def load(self):
        self.data = read_json(self.graph_path, self.graph_path.name)
        validate_graph(self.data, kind=self.kind, label=self.graph_path.name)

    def commit(self):
        self.refuse_if_in_package()
        validate_graph(self.data, kind=self.kind, label=self.graph_path.name)
        write_json_atomic(self.graph_path, self.data)
        if self.kind == "case":
            self.write_views()

    def say(self, text: str):
        self.notes.append(text)

    # ---- 视图（ADR-0011）
    def write_views(self):
        view = build_view(self.data, self.domain, self.graph_path.name)
        write_json_atomic(self.graph_path.with_name(VIEW_JSON), view)
        write_text_atomic(self.graph_path.with_name(VIEW_MD), render_markdown(view))

    # ---- 解析（含严格惰性带入）
    def domain_module_of(self, key: str):
        if self.domain is None:
            return None
        return find_module(self.domain, key)

    def domain_node_of(self, key: str):
        if self.domain is None:
            return None, None
        return find_node(self.domain, key)

    def bring_module(self, dm: dict) -> dict:
        """按领域图创建模块（不带任何节点），插进已有模块之间。"""
        m = {"id": dm["id"], "标题": dm["标题"], "节点": []}
        if dm["标题"] in module_titles(self.data):
            raise Rejected("图里已有标题为「%s」的模块，与领域图里的同名模块不是同一个（id 不同）" % dm["标题"])
        insert_by_domain_order(self.data["模块"], m, domain_order(self.domain))
        self.say("已按领域图带入模块「%s」" % m["标题"])
        return m

    def bring_node(self, dm: dict, dn: dict) -> dict:
        m = find_module(self.data, dm["id"]) or self.bring_module(dm)
        if dn["标题"] in node_titles(self.data):
            raise Rejected("图里已有标题为「%s」的节点，与领域图里的同名节点不是同一个（id 不同）" % dn["标题"])
        n = strip_for_case(dn)
        insert_by_domain_order(m["节点"], n, domain_order(self.domain))
        self.say("已按领域图带入节点「%s」到模块「%s」" % (n["标题"], m["标题"]))
        return n

    def resolve_module(self, key: str, *, create: bool = True) -> dict:
        m = find_module(self.data, key)
        if m is not None:
            return m
        dm = self.domain_module_of(key)
        if dm is not None and create:
            return self.bring_module(dm)
        raise Rejected("图里没有模块「%s」%s" % (key, "，领域图里也没有" if self.domain is not None else ""))

    def resolve_node(self, key: str, *, create: bool = True) -> Tuple[dict, dict]:
        m, n = find_node(self.data, key)
        if n is not None:
            return m, n
        dm, dn = self.domain_node_of(key)
        if dn is not None and create:
            n = self.bring_node(dm, dn)
            return find_node(self.data, n["id"])
        raise Rejected("图里没有节点「%s」%s" % (key, "，领域图里也没有" if self.domain is not None else ""))

    # ---- 构成：模块
    def add_module(self, title: str, id_: Optional[str], pos: Position):
        if title in module_titles(self.data):
            raise Rejected("图里已有模块「%s」" % title)
        self.check_id_option(id_)
        dm = self.domain_module_of(id_ or title) if self.domain is not None else None
        if dm is not None and (id_ is None or id_ == dm["id"]) and dm["标题"] == title:
            m = self.bring_module(dm)
        else:
            m = {"id": id_ or new_id("m"), "标题": title, "节点": []}
            self.check_new_id(m["id"])
            self.data["模块"].append(m)
            self.say("已新增模块「%s」（id %s）" % (title, m["id"]))
        if not pos.empty:
            self.place(self.data["模块"], m, pos)

    def rename_module(self, key: str, title: str):
        m = self.resolve_module(key)
        if title != m["标题"] and title in module_titles(self.data):
            raise Rejected("图里已有模块「%s」" % title)
        old, m["标题"] = m["标题"], title
        self.say("模块「%s」改名为「%s」" % (old, title))

    def move_module(self, key: str, pos: Position):
        m = self.resolve_module(key)
        self.place(self.data["模块"], m, pos)
        self.say("模块「%s」已排到位置 %d" % (m["标题"], self.data["模块"].index(m) + 1))

    def delete_module(self, key: str):
        m = self.resolve_module(key, create=False)
        if m["节点"]:
            raise Rejected("模块「%s」还有 %d 个节点，节点永不删：先用 move-node 把节点移走，或对模块记不适用" % (m["标题"], len(m["节点"])))
        self.data["模块"].remove(m)
        self.say("已删除空模块「%s」" % m["标题"])

    # ---- 构成：节点
    def add_node(self, module_key: str, title: str, id_: Optional[str], template: Optional[str],
                 time_limit: Optional[str], pos: Position):
        if title in node_titles(self.data):
            raise Rejected("图里已有节点「%s」" % title)
        self.check_id_option(id_)
        dm, dn = self.domain_node_of(id_ or title) if self.domain is not None else (None, None)
        if dn is not None and (id_ is None or id_ == dn["id"]) and dn["标题"] == title:
            target = self.resolve_module(module_key)
            if target["id"] != dm["id"]:
                raise Rejected("节点「%s」在领域图里属于模块「%s」；要放到「%s」请先带入再用 move-node 移动" % (title, dm["标题"], target["标题"]))
            n = self.bring_node(dm, dn)
        else:
            m = self.resolve_module(module_key)
            n = {"id": id_ or new_id("n"), "标题": title, "空白模板": parse_template(template or NO_TEMPLATE), "条目": []}
            self.check_new_id(n["id"])
            if time_limit:
                self.require_domain_kind("时限")
                n["时限"] = time_limit
            m["节点"].append(n)
            self.say("已在模块「%s」新增节点「%s」（id %s）" % (m["标题"], title, n["id"]))
        if template and n["空白模板"] != parse_template(template):
            n["空白模板"] = parse_template(template)
        if not pos.empty:
            m, n = find_node(self.data, n["id"])
            self.place(m["节点"], n, pos)

    def rename_node(self, key: str, title: str):
        _, n = self.resolve_node(key)
        if title != n["标题"] and title in node_titles(self.data):
            raise Rejected("图里已有节点「%s」" % title)
        old, n["标题"] = n["标题"], title
        self.say("节点「%s」改标题为「%s」（id %s 不变，条目不动）" % (old, title, n["id"]))

    def move_node(self, key: str, module_key: Optional[str], pos: Position):
        m, n = self.resolve_node(key)
        target = self.resolve_module(module_key) if module_key else m
        if target is not m:
            m["节点"].remove(n)
            target["节点"].append(n)
            self.say("节点「%s」从模块「%s」移到「%s」" % (n["标题"], m["标题"], target["标题"]))
        if not pos.empty:
            self.place(target["节点"], n, pos)
        self.say("节点「%s」现在在模块「%s」的第 %d 位" % (n["标题"], target["标题"], target["节点"].index(n) + 1))

    def set_template(self, key: str, template: str):
        _, n = self.resolve_node(key)
        n["空白模板"] = parse_template(template)
        self.say("节点「%s」的空白模板改为 %s" % (n["标题"], template_text(n["空白模板"])))

    def set_time_limit(self, key: str, time_limit: Optional[str]):
        self.require_domain_kind("时限")
        _, n = self.resolve_node(key)
        if time_limit:
            n["时限"] = time_limit
            self.say("节点「%s」的时限改为：%s" % (n["标题"], time_limit))
        else:
            n.pop("时限", None)
            self.say("节点「%s」的时限已清空" % n["标题"])

    # ---- 条目（只追加，来源由动作推出）
    def generate(self, key: str, doc: str, review: str, source: Optional[str], lawyer_written: bool):
        self.require_case_kind("追加条目")
        _, n = self.resolve_node(key)
        state = node_state(n)
        if state == STATE_NA:
            raise Rejected("节点「%s」已记不适用（终态），不能再生成" % n["标题"])
        for label, value in (("--doc", doc), ("--source", source), ("--review", review)):
            if value and not is_relative_path(value):
                raise Rejected("%s 须是相对工作区根的正斜杠路径（如 文书/<节点>/x-v1.docx），收到 %r" % (label, value))
        e = {"动作": "生成", "时间": now(), "来源": SOURCE_LAWYER if lawyer_written else SOURCE_AGENT, "文书": doc}
        if source:
            e["源"] = source
        e["审查报告"] = review
        n["条目"].append(e)
        self.say("已追加生成条目：节点「%s」第 %d 版（来源 %s），状态 %s%s" % (
            n["标题"], len(versions(n)), e["来源"], node_state(n),
            "，旧的确认留在历史里" if state == STATE_CONFIRMED else ""))

    def confirm(self, key: str, words: str):
        self.require_case_kind("追加条目")
        _, n = self.resolve_node(key, create=False)
        state = node_state(n)
        if state != STATE_GENERATED:
            raise Rejected("节点「%s」当前是 %s，只有已生成的节点能确认" % (n["标题"], state))
        n["条目"].append({"动作": "确认", "时间": now(), "来源": SOURCE_LAWYER, "原话": words})
        self.say("已追加确认条目：节点「%s」，状态 已确认，原话「%s」" % (n["标题"], words))

    def not_applicable(self, key: str, words: str):
        self.require_case_kind("追加条目")
        _, n = self.resolve_node(key)
        self.mark_na(n, words)
        self.say("已追加不适用条目：节点「%s」，状态 不适用（终态），原话「%s」" % (n["标题"], words))

    def mark_na(self, n: dict, words: str):
        state = node_state(n)
        if state == STATE_CONFIRMED:
            raise Rejected("节点「%s」已确认，不能不适用；要改就重出一版" % n["标题"])
        if state == STATE_NA:
            raise Rejected("节点「%s」已是不适用" % n["标题"])
        n["条目"].append({"动作": "不适用", "时间": now(), "来源": SOURCE_LAWYER, "原话": words})

    def not_applicable_module(self, key: str, words: str):
        """模块级不适用 = 该模块在领域图里的全部节点带进案件图、逐个记不适用（#7）。"""
        self.require_case_kind("追加条目")
        m = self.resolve_module(key)
        dm = self.domain_module_of(m["id"])
        if dm is not None:
            for dn in dm["节点"]:
                if find_node(self.data, dn["id"])[1] is None:
                    self.bring_node(dm, dn)
        if not m["节点"]:
            raise Rejected("模块「%s」没有节点，没有可记不适用的对象" % m["标题"])
        confirmed = [n["标题"] for n in m["节点"] if node_state(n) == STATE_CONFIRMED]
        if confirmed:
            raise Rejected("模块「%s」里已确认的节点不能不适用：%s" % (m["标题"], "、".join(confirmed)))
        count = 0
        for n in m["节点"]:
            if node_state(n) != STATE_NA:
                self.mark_na(n, words)
                count += 1
        self.say("模块「%s」不适用：%d 个节点各追加一条不适用条目，原话「%s」" % (m["标题"], count, words))

    # ---- 起手（三选一，ADR-0004）
    def init(self, empty: bool, full: bool, from_path: Optional[str], name: Optional[str]):
        if self.graph_path.exists():
            raise Rejected("%s 已存在，起手一案一次；要改图用别的子命令" % self.graph_path)
        if sum(bool(x) for x in (empty, full, from_path)) != 1:
            raise Rejected("起手三选一：--empty、--full（整份领域图）、--from <定制图路径>")
        if self.kind == "domain":
            if not empty or not name:
                raise Rejected("领域图起手只支持 --empty --name <领域名>")
            self.data = {"格式版本": FORMAT_VERSION, "领域": name, "模块": []}
            self.say("已建空领域图「%s」" % name)
            return
        if empty:
            domain_name = name or (self.domain["领域"] if self.domain else None)
            if domain_name is None:
                raise Rejected("空图起手要么给 --domain，要么给 --name <领域名>")
            self.data = {"格式版本": FORMAT_VERSION, "领域": domain_name, "模块": []}
            self.say("已建空图，领域「%s」" % domain_name)
            return
        if full:
            if self.domain is None:
                raise Rejected("--full 要带 --domain 指向领域图")
            source, label = self.domain, "领域图"
        else:
            path = pathlib.Path(from_path)
            source = read_json(path, "定制图")
            validate_graph(source, kind="domain", label="定制图 %s" % path.name)
            label = "定制图"
        self.data = {"格式版本": FORMAT_VERSION, "领域": name or source["领域"], "模块": [
            {"id": m["id"], "标题": m["标题"], "节点": [strip_for_case(n) for n in m["节点"]]} for m in source["模块"]]}
        self.say("已按%s整份起手：%d 个模块、%d 个节点，领域「%s」" % (
            label, len(self.data["模块"]), sum(len(m["节点"]) for m in self.data["模块"]), self.data["领域"]))

    # ---- 工具
    def check_new_id(self, id_: str):
        if not ID_RE.match(id_):
            raise Rejected("id %r 不合法：只用字母、数字、连字符、下划线、点" % id_)
        if id_ in all_ids(self.data):
            raise Rejected("id %s 已存在" % id_)

    def require_case_kind(self, what: str):
        if self.kind != "case":
            raise Rejected("%s只对案件图做；领域图没有条目（--kind domain）" % what)

    def require_domain_kind(self, what: str):
        if self.kind != "domain":
            raise Rejected("%s只住领域图；案件图不存、不拷贝（ADR-0016）。要改领域图用 --kind domain" % what)

    def refuse_if_in_package(self):
        """包内的出厂种子谁都不许写，没有例外（ADR-0020）。挡的是律师侧逐节点回流写进包里：
        那份图下一次 skill 包升级就被整个换掉，累计的东西静默消失，而律师这一侧没有 git 看得见。
        开发者定制领域图走的是同一条路：办一遍、回流进自己的活图，再入库，入库不经本引擎。
        只拦写：commit 之前才判，validate 与 views 读种子照旧（起手拿它当领域图来源也照旧）。"""
        if self.kind != "domain" or not in_package(self.graph_path):
            return
        raise Rejected(
            "这份领域图在 skill 包内（出厂种子 %s），种子谁都不许写（ADR-0020）：包一升级它就被整个换掉。"
            "律师累计的领域图住包外的活图 ~/.loo0ng/领域/<领域名>/，取它的路径用 skill \"loo0ng-domain\" 的 "
            "sketch.py home --name <领域名>；这个工作区的领域目录还指着种子的话，"
            "把 AGENTS.md 里「领域目录」那一行换成它回显的路径（换法见 skill \"loo0ng-setup-case\" 正文），"
            "换完才写得进去。开发者要改种子，也是先改自己的活图再入库，不在这里写。"
            % self.graph_path.resolve().parent.as_posix())

    def place(self, siblings: List[dict], item: dict, pos: Position):
        siblings.remove(item)
        if pos.first:
            siblings.insert(0, item)
        elif pos.last:
            siblings.append(item)
        else:
            ref_key = pos.before or pos.after
            ref = next((s for s in siblings if s["id"] == ref_key or s["标题"] == ref_key), None)
            if ref is None:
                siblings.append(item)
                raise Rejected("参照「%s」不在同一组兄弟里" % ref_key)
            idx = siblings.index(ref) + (1 if pos.after else 0)
            siblings.insert(idx, item)

    def check_id_option(self, id_: Optional[str]):
        """--id 只给领域图作者用；案件图里律师自加的 id 由引擎生成（ADR-0003），来源与时限按 id 查出才不会被冒名。"""
        if id_ and self.kind != "domain":
            raise Rejected("--id 只在 --kind domain 下可用；案件图里的 id 由引擎生成")


def parse_template(text: str):
    if text == NO_TEMPLATE:
        return NO_TEMPLATE
    source, sep, filename = text.partition(":")
    if not sep or source not in TEMPLATE_SOURCES or not filename.strip():
        raise Rejected("空白模板写法：无 | 官方:<文件名> | 生成:<文件名>，收到 %r" % text)
    return {"来源": source, "文件": filename.strip()}


def template_text(value) -> str:
    if value == NO_TEMPLATE:
        return NO_TEMPLATE
    return "%s %s" % (value["来源"], value["文件"])


# ---------------------------------------------------------------- 派生视图

def build_view(data, domain, source_name: str) -> dict:
    domain_ids = all_ids(domain) if domain else set()
    domain_nodes = {n["id"]: n for m in domain["模块"] for n in m["节点"]} if domain else {}

    def origin(id_):
        return ORIGIN_DOMAIN if id_ in domain_ids else ORIGIN_CASE

    def node_summary(n, state):
        """节点在视图里的公共形状：id、标题、来源、空白模板，时限按 id 从领域图查出，再加算好的状态。"""
        v = {"id": n["id"], "标题": n["标题"], "来源": origin(n["id"]), "空白模板": n["空白模板"]}
        dn = domain_nodes.get(n["id"])
        if dn is not None and "时限" in dn:
            v["时限"] = dn["时限"]
        v["状态"] = state
        return v

    def node_view(n):
        v = node_summary(n, node_state(n))
        v["文书版本"] = versions(n)
        v["条目"] = [dict(e) for e in n["条目"]]
        return v

    modules = []
    for m in data["模块"]:
        modules.append({"id": m["id"], "标题": m["标题"], "来源": origin(m["id"]),
                        "状态": module_state(m), "节点": [node_view(n) for n in m["节点"]]})

    ahead = []
    if domain:
        present = all_ids(data)
        for dm in domain["模块"]:
            missing = [n for n in dm["节点"] if n["id"] not in present]
            in_graph = find_module(data, dm["id"])
            if in_graph is not None and not missing:
                continue
            entry = {"id": dm["id"], "标题": dm["标题"], "来源": ORIGIN_DOMAIN,
                     "状态": MODULE_IN_GRAPH if in_graph is not None else STATE_AHEAD,
                     "节点": [node_summary(n, STATE_AHEAD) for n in missing]}
            ahead.append(entry)

    return {"格式版本": FORMAT_VERSION, "领域": data["领域"], "生成时间": now(), "源图": source_name,
            "模块": modules, "前方": ahead}


def render_markdown(view: dict) -> str:
    lines = ["# 图视图：%s" % (view["领域"] or "（未命名领域）"), "",
             "生成时间 %s，源图 %s，格式版本 %d。状态与来源都是算出来的，不存进图。" % (
                 view["生成时间"], view["源图"], view["格式版本"]), ""]
    if not view["模块"]:
        lines += ["（图里还没有模块）", ""]
    for m in view["模块"]:
        lines.append("## %s（%s，来源 %s）" % (m["标题"], m["状态"], m["来源"]))
        lines.append("")
        if not m["节点"]:
            lines.append("（空模块）")
        for n in m["节点"]:
            attrs = ["来源 %s" % n["来源"], "空白模板 %s" % template_text(n["空白模板"])]
            if "时限" in n:
                attrs.append("时限：%s" % n["时限"])
            lines.append("- **%s**：%s（%s）" % (n["标题"], n["状态"], "，".join(attrs)))
            for v in n["文书版本"]:
                parts = ["文书 %s" % v["文书"]]
                if "源" in v:
                    parts.append("源 %s" % v["源"])
                parts.append("审查报告 %s" % v["审查报告"])
                lines.append("  - 第 %d 版：%s" % (v["版本"], "，".join(parts)))
            for e in n["条目"]:
                if e["动作"] == "生成":
                    lines.append("  - %s 生成（%s）" % (e["时间"], e["来源"]))
                else:
                    lines.append("  - %s %s（%s）：「%s」" % (e["时间"], e["动作"], e["来源"], e["原话"]))
        lines.append("")
    lines.append("## 前方")
    lines.append("")
    lines.append("领域图里有、案件图里还没有的模块与节点；不在图里，做到时才按领域图带入。")
    lines.append("")
    if not view["前方"]:
        lines.append("（无）")
    for m in view["前方"]:
        lines.append("- 模块 **%s**（%s）" % (m["标题"], m["状态"]))
        for n in m["节点"]:
            attrs = ["空白模板 %s" % template_text(n["空白模板"])]
            if "时限" in n:
                attrs.append("时限：%s" % n["时限"])
            lines.append("  - %s（%s，%s）" % (n["标题"], n["状态"], "，".join(attrs)))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="graph.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graph", default=DEFAULT_GRAPH, help="图文件，默认当前目录的 图.json")
    ap.add_argument("--domain", default=None, help="领域图 JSON 或领域目录（含 领域图.json）；案件图有它才有前方与惰性带入")
    ap.add_argument("--kind", choices=("case", "domain"), default="case",
                    help="case 案件图（默认，写完重算两份视图）；domain 领域图（可带时限、无条目、不出视图）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="起手：--empty | --full | --from 路径")
    p.add_argument("--empty", action="store_true", help="空图")
    p.add_argument("--full", action="store_true", help="整份领域图（人的选择，不受惰性约束）")
    p.add_argument("--from", dest="from_path", help="开发者交付的定制图（领域图格式）")
    p.add_argument("--name", help="领域名；空图无 --domain 时必填，领域图起手必填")

    sub.add_parser("validate", help="只校验，不写")
    sub.add_parser("views", help="只重算两份视图（案件图）")

    p = sub.add_parser("add-module", help="新增模块；标题与领域图里某模块相同则按领域图带入")
    p.add_argument("--title", required=True)
    p.add_argument("--id", help="只对 --kind domain；案件图的 id 由引擎生成")
    p.add_argument("--before")
    p.add_argument("--after")

    p = sub.add_parser("rename-module")
    p.add_argument("--module", required=True, help="模块 id 或标题")
    p.add_argument("--title", required=True)

    p = sub.add_parser("move-module", help="模块排序")
    p.add_argument("--module", required=True)
    p.add_argument("--before")
    p.add_argument("--after")
    p.add_argument("--first", action="store_true")
    p.add_argument("--last", action="store_true")

    p = sub.add_parser("delete-module", help="删空模块（有节点即拒）")
    p.add_argument("--module", required=True)

    p = sub.add_parser("add-node", help="新增节点；标题与领域图里某节点相同则按领域图带入")
    p.add_argument("--module", required=True, help="模块 id 或标题；只在领域图里的模块会一并带入")
    p.add_argument("--title", required=True)
    p.add_argument("--id", help="只对 --kind domain；案件图的 id 由引擎生成")
    p.add_argument("--template", help="无 | 官方:<文件名> | 生成:<文件名>")
    p.add_argument("--time-limit", help="时限一句话，只对 --kind domain")
    p.add_argument("--before")
    p.add_argument("--after")

    p = sub.add_parser("rename-node")
    p.add_argument("--node", required=True, help="节点 id 或标题")
    p.add_argument("--title", required=True)

    p = sub.add_parser("move-node", help="节点排序或跨模块移动")
    p.add_argument("--node", required=True)
    p.add_argument("--module", help="目标模块，不给就在原模块内排序")
    p.add_argument("--before")
    p.add_argument("--after")
    p.add_argument("--first", action="store_true")
    p.add_argument("--last", action="store_true")

    p = sub.add_parser("set-template", help="改空白模板属性")
    p.add_argument("--node", required=True)
    p.add_argument("--template", required=True, help="无 | 官方:<文件名> | 生成:<文件名>")

    p = sub.add_parser("set-time-limit", help="改时限句，只对 --kind domain")
    p.add_argument("--node", required=True)
    p.add_argument("--time-limit", help="不给即清空")

    p = sub.add_parser("generate", help="追加生成条目（来源 agent；--lawyer-written 则来源律师）")
    p.add_argument("--node", required=True)
    p.add_argument("--doc", required=True, help="文书相对路径（相对工作区根）")
    p.add_argument("--review", required=True, help="审查报告相对路径")
    p.add_argument("--source", help="Markdown 源相对路径，兜底件可无")
    p.add_argument("--lawyer-written", action="store_true", help="律师自写的兜底件")

    p = sub.add_parser("confirm", help="追加确认条目（律师原话）")
    p.add_argument("--node", required=True)
    p.add_argument("--words", required=True, help="律师那句话，原样存")

    p = sub.add_parser("not-applicable", help="追加不适用条目：--node 单个节点，或 --module 整个模块")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--node")
    g.add_argument("--module")
    p.add_argument("--words", required=True, help="律师那句话，原样存")
    return ap


def run(args) -> List[str]:
    engine = Engine(pathlib.Path(args.graph), resolve_domain_path(args.domain), args.kind)
    if args.cmd == "init":
        engine.init(args.empty, args.full, args.from_path, args.name)
        engine.commit()
        return engine.notes
    engine.load()
    if args.cmd == "validate":
        return ["%s 合校验" % engine.graph_path.name]
    if args.cmd == "views":
        engine.require_case_kind("重算视图")
        engine.write_views()
        return ["已重算 %s 与 %s" % (VIEW_MD, VIEW_JSON)]
    if args.cmd == "add-module":
        engine.add_module(args.title, args.id, Position.from_args(args))
    elif args.cmd == "rename-module":
        engine.rename_module(args.module, args.title)
    elif args.cmd == "move-module":
        engine.move_module(args.module, Position.from_args(args))
    elif args.cmd == "delete-module":
        engine.delete_module(args.module)
    elif args.cmd == "add-node":
        engine.add_node(args.module, args.title, args.id, args.template, args.time_limit, Position.from_args(args))
    elif args.cmd == "rename-node":
        engine.rename_node(args.node, args.title)
    elif args.cmd == "move-node":
        engine.move_node(args.node, args.module, Position.from_args(args))
    elif args.cmd == "set-template":
        engine.set_template(args.node, args.template)
    elif args.cmd == "set-time-limit":
        engine.set_time_limit(args.node, args.time_limit)
    elif args.cmd == "generate":
        engine.generate(args.node, args.doc, args.review, args.source, args.lawyer_written)
    elif args.cmd == "confirm":
        engine.confirm(args.node, args.words)
    elif args.cmd == "not-applicable":
        if args.module:
            engine.not_applicable_module(args.module, args.words)
        else:
            engine.not_applicable(args.node, args.words)
    engine.commit()
    return engine.notes


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        notes = run(args)
    except Invalid as e:
        print("拒写：%s。文件不合校验，引擎不猜；律师手改 图.json 不受支持，请从上一次能用的状态重来。" % e, file=sys.stderr)
        return 1
    except Rejected as e:
        print("拒写：%s" % e, file=sys.stderr)
        return 1
    for line in notes:
        print(line)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
