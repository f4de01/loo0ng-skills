#!/usr/bin/env python3
"""图引擎 CLI：案件图与预设图的唯一写入缝。标准库零依赖，Windows 中文路径可用。

图是工作区根的单一 JSON 图.json（ADR-0003）：顶层只有 格式版本、模块；模块内嵌节点，节点内嵌条目。
起手之后案件图自足（ADR-0023）：状态、前方、时限、目录名全部只从图自己的内容算，不再读图外的任何东西。
条目只追加（生成 / 确认 / 不适用），状态只算不存；每次写图后覆盖重算 图视图.md 与 图视图.json（ADR-0011）。
字段表与最小样例见 ../references/格式.md。

用法：
  python graph.py [--graph 图.json] [--kind case|preset] <子命令> ...

子命令（--help 看各自参数）：
  init            起手：--empty | --preset <预设图目录>
  validate        只校验不写
  views           只重算两份视图
  export-preset   另存：把当前图剥成一份预设图
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
import zipfile
from typing import Dict, List, Optional, Tuple

FORMAT_VERSION = 2  # 图.json 与 图视图.json 共用，同步升（ADR-0011）。2 起案件图自足（ADR-0023）
DEFAULT_GRAPH = "图.json"
PRESET_FILENAME = "预设图.json"
# 包内出厂预设图的判据（ADR-0020 的拒写，路径按 ADR-0023 换成预设图的形状）。
# 同一套判据在 skill "setup-case" 与 skill "domain" 侧也有一份（那边只报不拒）：改这里要改那两处。
PRESET_ASSETS_DIRNAME = "预设图"
ASSETS_DIRNAME = "assets"
PRESET_ROOT_RELATIVE = pathlib.Path("..") / ".." / "domain" / ASSETS_DIRNAME / PRESET_ASSETS_DIRNAME
VIEW_MD = "图视图.md"
VIEW_JSON = "图视图.json"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

NO_TEMPLATE = "无"
ACTIONS = ("生成", "确认", "不适用")
SOURCE_AGENT, SOURCE_LAWYER = "agent", "律师"
STATE_NONE, STATE_GENERATED, STATE_CONFIRMED, STATE_NA = "未生成", "已生成", "已确认", "不适用"
MODULE_NA, MODULE_DONE, MODULE_ACTIVE = "不适用", "已完成", "进行中"
HL_NO_DOC, HL_LEFT, HL_CLEAR = "无文书", "未清", "已清"

GRAPH_KEYS = {"格式版本", "模块"}
MODULE_KEYS = {"id", "标题", "节点"}
NODE_KEYS = {"id", "标题", "空白模板", "条目"}
NODE_OPTIONAL = {"时限"}
ENTRY_KEYS = {
    "生成": {"动作", "时间", "来源", "文书", "审查报告"},
    "确认": {"动作", "时间", "来源", "原话"},
    "不适用": {"动作", "时间", "来源", "原话"},
}

# 目录名转义：这九个字符在 Windows 或 POSIX 的目录名里用不了，一律换成同形的全角（ADR-0023）。
# 全仓只有这一份表：文书目录、模板拷贝、视图里的 目录名 列都读它，别处不许再定一份。
DIRNAME_ESCAPES = {
    "/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？",
    '"': "＂", "<": "＜", ">": "＞", "|": "｜",
}


class Rejected(Exception):
    """引擎拒写：规则不允许，或文件不合校验。文件一字不动。"""


class Invalid(Rejected):
    pass


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


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return "%s-%s" % (prefix, secrets.token_hex(4))


def dirname_of(title: str) -> str:
    """标题做目录名：只把用不了的字符换成全角，别的一个不动（ADR-0023）。"""
    out = title
    for bad, good in DIRNAME_ESCAPES.items():
        out = out.replace(bad, good)
    return out


# ---------------------------------------------------------------- 校验

def _check(cond, msg):
    if not cond:
        raise Invalid(msg)


def validate_graph(data, *, kind: str, label: str) -> None:
    """kind 是 case 或 preset。预设图不得有条目；时限两边都可带，案件图那份由起手拷入。"""
    _check(isinstance(data, dict), "%s 顶层须是对象" % label)
    # 先查版本再查键：旧版本的图字段本来就不一样，先报「版本不对」才说得清楚
    _check("格式版本" in data, "%s 顶层没有 格式版本" % label)
    _check(data["格式版本"] == FORMAT_VERSION and isinstance(data["格式版本"], int)
           and not isinstance(data["格式版本"], bool),
           "%s 的格式版本是 %r，本引擎只认 %d；旧版本的图没有升级路径，"
           "从预设图重新起手（ADR-0023）" % (label, data["格式版本"], FORMAT_VERSION))
    _check(set(data) == GRAPH_KEYS,
           "%s 顶层键须恰为 格式版本、模块，实际：%s%s" % (
               label, "、".join(sorted(data)),
               "（领域自格式版本 2 起不是图的字段，ADR-0023）" if "领域" in data else ""))
    _check(isinstance(data["模块"], list), "%s 的 模块 须是数组" % label)
    ids = set()
    module_titles_seen, node_titles_seen = {}, {}
    for m in data["模块"]:
        _check(isinstance(m, dict) and set(m) == MODULE_KEYS, "%s 里模块的键须恰为 id、标题、节点" % label)
        _check(isinstance(m["id"], str) and ID_RE.match(m["id"]), "%s 里模块 id %r 不合法" % (label, m["id"]))
        _check(m["id"] not in ids, "%s 里 id %s 重复" % (label, m["id"]))
        ids.add(m["id"])
        _check(isinstance(m["标题"], str) and m["标题"].strip(), "%s 里模块 %s 标题为空" % (label, m["id"]))
        check_title_unique(module_titles_seen, m["标题"], label, "模块")
        _check(isinstance(m["节点"], list), "%s 里模块「%s」的 节点 须是数组" % (label, m["标题"]))
        for n in m["节点"]:
            _check(isinstance(n, dict), "%s 里节点须是对象" % label)
            missing = NODE_KEYS - set(n)
            _check(not missing, "%s 里节点缺键：%s" % (label, "、".join(sorted(missing))))
            extra = set(n) - (NODE_KEYS | NODE_OPTIONAL)
            _check(not extra, "%s 里节点「%s」有未知键：%s" % (label, n.get("标题"), "、".join(sorted(extra))))
            _check(isinstance(n["id"], str) and ID_RE.match(n["id"]), "%s 里节点 id %r 不合法" % (label, n["id"]))
            _check(n["id"] not in ids, "%s 里 id %s 重复" % (label, n["id"]))
            ids.add(n["id"])
            _check(isinstance(n["标题"], str) and n["标题"].strip(), "%s 里节点 %s 标题为空" % (label, n["id"]))
            check_title_unique(node_titles_seen, n["标题"], label, "节点")
            validate_template(n["空白模板"], label, n["标题"])
            if "时限" in n:
                _check(isinstance(n["时限"], str) and n["时限"].strip(),
                       "%s 里节点「%s」的 时限 须是非空字符串" % (label, n["标题"]))
            _check(isinstance(n["条目"], list), "%s 里节点「%s」的 条目 须是数组" % (label, n["标题"]))
            if kind == "preset":
                _check(not n["条目"], "%s 是预设图，节点「%s」不得有条目" % (label, n["标题"]))
            validate_entries(n["条目"], label, n["标题"])


def check_title_unique(seen: Dict[str, str], title: str, label: str, what: str) -> None:
    """标题图内唯一，转义成目录名之后也唯一：否则两个节点会抢同一个文书目录。"""
    _check(title not in seen.values(), "%s 里%s标题「%s」重复" % (label, what, title))
    key = dirname_of(title)
    _check(key not in seen, "%s 里%s标题「%s」与「%s」转义后是同一个目录名「%s」"
           % (label, what, title, seen.get(key), key))
    seen[key] = title


def is_relative_path(text: str) -> bool:
    """相对工作区根、正斜杠、不向上越界。Windows 上 os.path.isabs 不认无盘符的 /x，所以另查开头。"""
    return not (os.path.isabs(text) or text.startswith("/") or "\\" in text or text.startswith("../")
                or text == ".." or "/../" in text or (len(text) > 1 and text[1] == ":"))


def validate_template(value, label, title):
    """空白模板只记文件名（ADR-0023）：文件住 参考/模板/ 下，图不记来源、不记路径。"""
    if value == NO_TEMPLATE:
        return
    if isinstance(value, dict):
        raise Invalid("%s 里节点「%s」的 空白模板 还是「来源 + 文件」的旧写法；"
                      "自格式版本 2 起只记文件名（ADR-0023）" % (label, title))
    _check(isinstance(value, str) and value.strip(),
           "%s 里节点「%s」的 空白模板 须是「无」或一个文件名" % (label, title))
    _check("/" not in value and "\\" not in value,
           "%s 里节点「%s」的 空白模板 只写文件名，不带路径：%r" % (label, title, value))


def validate_entries(entries, label, title):
    state = STATE_NONE
    for e in entries:
        _check(isinstance(e, dict) and e.get("动作") in ACTIONS, "%s 里节点「%s」有条目的 动作 不合法" % (label, title))
        if e["动作"] == "生成" and "源" in e:
            raise Invalid("%s 里节点「%s」的生成条目还带 源：文书覆盖不迭代，没有 Markdown 源了（ADR-0023）"
                          % (label, title))
        _check(set(e) == ENTRY_KEYS[e["动作"]],
               "%s 里节点「%s」的 %s 条目键不对：%s" % (label, title, e["动作"], "、".join(sorted(e))))
        for k in set(e) - {"动作"}:
            _check(isinstance(e[k], str) and e[k], "%s 里节点「%s」条目的 %s 须是非空字符串" % (label, title, k))
        for k in ("文书", "审查报告"):
            if k in e:
                _check(is_relative_path(e[k]),
                       "%s 里节点「%s」条目的 %s 须是相对工作区根的正斜杠路径：%r" % (label, title, k, e[k]))
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


def last_generation(node) -> Optional[dict]:
    """最近一次生成，附它是第几次：文书覆盖同一路径，留痕只在条目里（ADR-0023）。"""
    gens = [e for e in node["条目"] if e["动作"] == "生成"]
    if not gens:
        return None
    e = gens[-1]
    return {"次数": len(gens), "时间": e["时间"], "来源": e["来源"], "文书": e["文书"], "审查报告": e["审查报告"]}


def last_confirmation(node) -> Optional[dict]:
    if node_state(node) != STATE_CONFIRMED:
        return None
    e = node["条目"][-1]
    return {"时间": e["时间"], "原话": e["原话"]}


# ---------------------------------------------------------------- 高亮（只用标准库读 docx）

HIGHLIGHT_RE = re.compile(br'<w:highlight[^>]*w:val="(?!none")')


def highlight_state(node, root: pathlib.Path) -> str:
    """节点当前文书里还有没有高亮：没有文书就是 无文书，扫不出高亮就是 已清。

    docx 是个 zip，正文在 word/document.xml；高亮是 run 属性 <w:highlight w:val="yellow"/>，
    去黄写成 val="none" 或整个属性不在。这里只认「有没有非 none 的 highlight」，不区分颜色：
    模板自带的黄与 agent 加的黄是同一种标记，律师去黄两种写法都算去掉了。
    只扫正文（word/document.xml）：高亮标的是律师要动手的地方，那些位置都在正文里；
    页眉页脚不扫。读不出来的文件按 未清 算：证不出已清就不能说已清，这一列是提示律师去看
    那份文书，不是裁定。"""
    gen = last_generation(node)
    if gen is None:
        return HL_NO_DOC
    path = root / gen["文书"]
    if not path.is_file():
        return HL_NO_DOC
    try:
        with zipfile.ZipFile(str(path)) as z:
            xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError, OSError):
        return HL_LEFT
    return HL_LEFT if HIGHLIGHT_RE.search(xml) else HL_CLEAR


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
    write_text_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
    try:
        # 显式 open：Path.write_text 的 newline= 是 3.10 才有的，律师那台 mac 是 3.9（#61）
        with open(str(tmp), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(str(tmp), str(path))
    finally:
        if tmp.exists():
            tmp.unlink()


def in_package(path: pathlib.Path) -> bool:
    """这份预设图是不是包内的出厂件。两条判据取或：兄弟 skill 的 assets/预设图/ 下（按本脚本的
    位置算，装在哪儿都成立），或者目录名摆成 <...>/assets/预设图/<名>（别处拷来的一份包）。"""
    d = path.resolve().parent
    sibling = (pathlib.Path(__file__).resolve().parent / PRESET_ROOT_RELATIVE).resolve()
    try:
        d.relative_to(sibling)
        return True
    except ValueError:
        pass
    return d.parent.name == PRESET_ASSETS_DIRNAME and d.parent.parent.name == ASSETS_DIRNAME


def resolve_preset_path(arg: str) -> pathlib.Path:
    """引擎收的是预设图目录；名与归属到路径的解析归 skill "domain"，不在这里。"""
    p = pathlib.Path(arg)
    return p / PRESET_FILENAME if p.is_dir() else p


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


def bare_node(node: dict) -> dict:
    """一个只有构成的节点：id、标题、空白模板、时限（有则），条目为空。

    两处共用：整份拷入案件图（预设图 -> 案件图）与另存（案件图 -> 预设图）。两边都靠它，
    「起手拷进来的与另存剥出去的是同一组字段」这句话才在代码里只有一个出处。"""
    n = {"id": node["id"], "标题": node["标题"], "空白模板": node["空白模板"], "条目": []}
    if "时限" in node:
        n["时限"] = node["时限"]
    return n


def bare_graph(data: dict) -> dict:
    return {"格式版本": FORMAT_VERSION, "模块": [
        {"id": m["id"], "标题": m["标题"], "节点": [bare_node(n) for n in m["节点"]]}
        for m in data["模块"]]}


# ---------------------------------------------------------------- 引擎

class Engine:
    def __init__(self, graph_path: pathlib.Path, kind: str):
        self.graph_path = graph_path
        self.kind = kind
        self.data = None
        self.notes = []  # 回显

    # ---- 生命周期
    def load(self):
        self.data = read_json(self.graph_path, self.graph_path.name)
        validate_graph(self.data, kind=self.kind, label=self.graph_path.name)

    def commit(self):
        if self.kind == "preset":
            self.refuse_if_in_package(self.graph_path)
        validate_graph(self.data, kind=self.kind, label=self.graph_path.name)
        write_json_atomic(self.graph_path, self.data)
        if self.kind == "case":
            self.write_views()

    def say(self, text: str):
        self.notes.append(text)

    # ---- 视图（ADR-0011）
    def write_views(self):
        view = build_view(self.data, self.graph_path)
        write_json_atomic(self.graph_path.with_name(VIEW_JSON), view)
        write_text_atomic(self.graph_path.with_name(VIEW_MD), render_markdown(view))

    # ---- 解析（图自足：图里没有就是没有，不去别处找）
    def resolve_module(self, key: str) -> dict:
        m = find_module(self.data, key)
        if m is None:
            raise Rejected("图里没有模块「%s」；要加用 add-module" % key)
        return m

    def resolve_node(self, key: str) -> Tuple[dict, dict]:
        m, n = find_node(self.data, key)
        if n is None:
            raise Rejected("图里没有节点「%s」；要加用 add-node" % key)
        return m, n

    # ---- 标题
    def check_title(self, title: str, what: str, 原标题: Optional[str] = None):
        """命令层先拦一遍标题：空的、重的、转义后撞车的。

        同样三条 validate_graph 也查，但那一层的拒绝消息说的是「文件被手改过」；
        律师打错一句话时该看见的是这句话哪里不对，所以这里先拦。"""
        已有 = (module_titles if what == "模块" else node_titles)(self.data) - {原标题}
        if not title.strip():
            raise Rejected("%s标题不能是空的" % what)
        if title in 已有:
            raise Rejected("图里已有%s「%s」" % (what, title))
        撞上 = next((t for t in 已有 if dirname_of(t) == dirname_of(title)), None)
        if 撞上 is not None:
            raise Rejected("%s「%s」与图里的「%s」转义成同一个目录名「%s」，两个会抢同一个文书目录：换一个标题"
                           % (what, title, 撞上, dirname_of(title)))

    # ---- 构成：模块
    def add_module(self, title: str, id_: Optional[str], pos: Position):
        self.check_title(title, "模块")
        self.check_id_option(id_)
        m = {"id": id_ or new_id("m"), "标题": title, "节点": []}
        self.check_new_id(m["id"])
        self.data["模块"].append(m)
        self.say("已新增模块「%s」（id %s）" % (title, m["id"]))
        if not pos.empty:
            self.place(self.data["模块"], m, pos)

    def rename_module(self, key: str, title: str):
        m = self.resolve_module(key)
        self.check_title(title, "模块", m["标题"])
        old, m["标题"] = m["标题"], title
        self.say("模块「%s」改名为「%s」" % (old, title))

    def move_module(self, key: str, pos: Position):
        m = self.resolve_module(key)
        self.place(self.data["模块"], m, pos)
        self.say("模块「%s」已排到位置 %d" % (m["标题"], self.data["模块"].index(m) + 1))

    def delete_module(self, key: str):
        m = self.resolve_module(key)
        if m["节点"]:
            raise Rejected("模块「%s」还有 %d 个节点，节点永不删：先用 move-node 把节点移走，或对模块记不适用"
                           % (m["标题"], len(m["节点"])))
        self.data["模块"].remove(m)
        self.say("已删除空模块「%s」" % m["标题"])

    # ---- 构成：节点
    def add_node(self, module_key: str, title: str, id_: Optional[str], template: Optional[str],
                 time_limit: Optional[str], pos: Position):
        self.check_title(title, "节点")
        self.check_id_option(id_)
        m = self.resolve_module(module_key)
        n = {"id": id_ or new_id("n"), "标题": title,
             "空白模板": parse_template(template or NO_TEMPLATE), "条目": []}
        self.check_new_id(n["id"])
        if time_limit:
            self.require_preset_kind("写时限")
            n["时限"] = time_limit
        m["节点"].append(n)
        self.say("已在模块「%s」新增节点「%s」（id %s）" % (m["标题"], title, n["id"]))
        if not pos.empty:
            self.place(m["节点"], n, pos)

    def rename_node(self, key: str, title: str):
        _, n = self.resolve_node(key)
        self.check_title(title, "节点", n["标题"])
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
        self.say("节点「%s」的空白模板改为 %s" % (n["标题"], n["空白模板"]))

    def set_time_limit(self, key: str, time_limit: Optional[str]):
        self.require_preset_kind("写时限")
        _, n = self.resolve_node(key)
        if time_limit:
            n["时限"] = time_limit
            self.say("节点「%s」的时限改为：%s" % (n["标题"], time_limit))
        else:
            n.pop("时限", None)
            self.say("节点「%s」的时限已清空" % n["标题"])

    # ---- 条目（只追加，来源由动作推出）
    def generate(self, key: str, doc: str, review: str, lawyer_written: bool):
        self.require_case_kind("追加条目")
        _, n = self.resolve_node(key)
        state = node_state(n)
        if state == STATE_NA:
            raise Rejected("节点「%s」已记不适用（终态），不能再生成" % n["标题"])
        for label, value in (("--doc", doc), ("--review", review)):
            if not is_relative_path(value):
                raise Rejected("%s 须是相对工作区根的正斜杠路径（如 文书/<模块>/<节点>/<节点>.docx），收到 %r"
                               % (label, value))
        n["条目"].append({"动作": "生成", "时间": now(),
                          "来源": SOURCE_LAWYER if lawyer_written else SOURCE_AGENT,
                          "文书": doc, "审查报告": review})
        self.say("已追加生成条目：节点「%s」第 %d 次生成（来源 %s），状态 %s%s" % (
            n["标题"], last_generation(n)["次数"], n["条目"][-1]["来源"], node_state(n),
            "，旧的确认留在条目里" if state == STATE_CONFIRMED else ""))

    def confirm(self, key: str, words: str):
        self.require_case_kind("追加条目")
        _, n = self.resolve_node(key)
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
        """模块级不适用 = 模块里每个节点各记一条不适用（#7）。图自足，没有要先带入的东西。"""
        self.require_case_kind("追加条目")
        m = self.resolve_module(key)
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

    # ---- 起手（二选一，ADR-0023）
    def init(self, empty: bool, preset_arg: Optional[str]):
        if self.graph_path.exists():
            raise Rejected("%s 已存在，起手一案一次；要改图用别的子命令" % self.graph_path)
        if bool(empty) == bool(preset_arg):
            raise Rejected("起手二选一：--empty（空图），或 --preset <预设图目录>（整份拷入）")
        if empty:
            self.data = {"格式版本": FORMAT_VERSION, "模块": []}
            self.say("已建空图")
            return
        if self.kind != "case":
            raise Rejected("--preset 只对案件图；预设图自己起手用 --empty")
        path = resolve_preset_path(preset_arg)
        source = read_json(path, "预设图")
        try:
            validate_graph(source, kind="preset", label="预设图 %s" % path.name)
        except Invalid as e:
            raise Rejected("预设图不合校验：%s；案件图一字未动" % e) from e
        self.data = bare_graph(source)
        self.say("已按预设图 %s 整份起手：%d 个模块、%d 个节点，空白模板与时限句一次到位" % (
            path.parent.name, len(self.data["模块"]), sum(len(m["节点"]) for m in self.data["模块"])))

    # ---- 另存（ADR-0023）
    def export_preset(self, out_arg: str):
        out = pathlib.Path(out_arg)
        target = out / PRESET_FILENAME if (out.is_dir() or not out.suffix) else out
        self.refuse_if_in_package(target)
        if target.exists():
            raise Rejected("%s 已存在，另存不覆盖：换个名字，或先把旧的移走" % target)
        preset = bare_graph(self.data)
        validate_graph(preset, kind="preset", label="另存出的预设图")
        target.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(target, preset)
        self.say("已另存预设图 %s：%d 个模块、%d 个节点；条目与不适用记录都剥掉了，%s 一字未动" % (
            target, len(preset["模块"]), sum(len(m["节点"]) for m in preset["模块"]), self.graph_path.name))

    # ---- 工具
    def check_new_id(self, id_: str):
        if not ID_RE.match(id_):
            raise Rejected("id %r 不合法：只用字母、数字、连字符、下划线、点" % id_)
        if id_ in all_ids(self.data):
            raise Rejected("id %s 已存在" % id_)

    def require_case_kind(self, what: str):
        if self.kind != "case":
            raise Rejected("%s只对案件图做；预设图没有条目（--kind preset）" % what)

    def require_preset_kind(self, what: str):
        if self.kind != "preset":
            raise Rejected("%s只在预设图上；案件图的时限由起手整份拷入，律师不在案件图上写它"
                           "（ADR-0016、ADR-0023）。要改预设图用 --kind preset" % what)

    def refuse_if_in_package(self, path: pathlib.Path):
        """包内的出厂预设图谁都不许写，没有例外（ADR-0020、ADR-0023）：包一升级它就被整个换掉，
        写进去的东西静默消失，而律师这一侧没有 git 看得见。个人预设图在另一个目录，物理上碰不到。
        两处调它：预设图的 commit，与另存的落点（另存是从案件图跑的，看的是目标不是本图）。
        案件图不归这条管：案件图落进仓库是另一条硬边界的病，该在起手那一刻拦，不该在第 37 条
        条目落盘时才报。只拦写：validate、views 与拿它起手（--preset 指着它）照旧。"""
        if not in_package(path):
            return
        raise Rejected(
            "%s 在 skill 包内（出厂预设图），出厂件谁都不许写（ADR-0020、ADR-0023）：包一升级它就被整个换掉。"
            "律师自己的图用 export-preset 另存成个人预设图，落在本机的个人预设图目录下，"
            "取它的路径调 skill \"domain\"；开发者要改出厂件，也是先写个人预设图，再经 PR 进仓库。"
            % path.resolve().parent.as_posix())

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
        """--id 只给预设图作者用；案件图里律师自加的 id 由引擎生成（ADR-0003）。"""
        if id_ and self.kind != "preset":
            raise Rejected("--id 只在 --kind preset 下可用；案件图里的 id 由引擎生成")


def parse_template(text: str):
    """空白模板写法：无 | <文件名>。带路径或旧的「官方:x.docx」都拒。"""
    head, sep, rest = text.partition(":")
    if sep and head in ("官方", "生成"):
        raise Rejected("空白模板不再分官方与生成两格，只记文件名（ADR-0023）：把 %r 写成 %r"
                       % (text, rest.strip() or "<文件名>"))
    if text == NO_TEMPLATE:
        return NO_TEMPLATE
    if not text.strip() or "/" in text or "\\" in text:
        raise Rejected("空白模板写法：无 | <文件名>（文件住 参考/模板/ 下，这里不带路径），收到 %r" % text)
    return text.strip()


# ---------------------------------------------------------------- 派生视图

def build_view(data, graph_path: pathlib.Path) -> dict:
    """图每次写完整体重算。状态、目录名、高亮、前方都在这里算一次，插件不自己算（ADR-0011）。"""
    root = graph_path.parent

    def composition(item):
        v = {"id": item["id"], "标题": item["标题"], "目录名": dirname_of(item["标题"])}
        if "空白模板" in item:
            v["空白模板"] = item["空白模板"]
        if "时限" in item:
            v["时限"] = item["时限"]
        return v

    def node_view(n):
        v = composition(n)
        v["状态"] = node_state(n)
        v["高亮"] = highlight_state(n, root)
        gen, conf = last_generation(n), last_confirmation(n)
        if gen is not None:
            v["最近生成"] = gen
        if conf is not None:
            v["最近确认"] = conf
        v["条目"] = [dict(e) for e in n["条目"]]
        return v

    modules, ahead = [], []
    for m in data["模块"]:
        view_m = composition(m)
        view_m["状态"] = module_state(m)
        view_m["节点"] = [node_view(n) for n in m["节点"]]
        modules.append(view_m)
        pending = [n for n in m["节点"] if node_state(n) == STATE_NONE]
        if pending:
            ahead_m = composition(m)
            ahead_m["节点"] = [composition(n) for n in pending]
            ahead.append(ahead_m)

    return {"格式版本": FORMAT_VERSION, "生成时间": now(), "源图": graph_path.name,
            "模块": modules, "前方": ahead}


def render_markdown(view: dict) -> str:
    lines = ["# 图视图", "",
             "生成时间 %s，源图 %s，格式版本 %d。状态、目录名、高亮、前方都是算出来的，不存进图。" % (
                 view["生成时间"], view["源图"], view["格式版本"]), ""]
    if not view["模块"]:
        lines += ["（图里还没有模块）", ""]
    for m in view["模块"]:
        lines += ["## %s（%s）" % (m["标题"], m["状态"]), ""]
        if not m["节点"]:
            lines.append("（空模块）")
        for n in m["节点"]:
            attrs = ["空白模板 %s" % n["空白模板"], "高亮%s" % n["高亮"]]
            if "时限" in n:
                attrs.append("时限：%s" % n["时限"])
            lines.append("- **%s**：%s（%s）" % (n["标题"], n["状态"], "，".join(attrs)))
            gen = n.get("最近生成")
            if gen is not None:
                lines.append("  - 最近生成：%s（第 %d 次，%s），文书 %s，审查报告 %s"
                             % (gen["时间"], gen["次数"], gen["来源"], gen["文书"], gen["审查报告"]))
            conf = n.get("最近确认")
            if conf is not None:
                lines.append("  - 最近确认：%s，「%s」" % (conf["时间"], conf["原话"]))
            for e in n["条目"]:
                if e["动作"] == "生成":
                    lines.append("  - %s 生成（%s）" % (e["时间"], e["来源"]))
                else:
                    lines.append("  - %s %s（%s）：「%s」" % (e["时间"], e["动作"], e["来源"], e["原话"]))
        lines.append("")
    lines += ["## 前方", "", "案件图里还没生成的节点，按图序；已确认与不适用的不在这里。", ""]
    if not view["前方"]:
        lines.append("（无）")
    for m in view["前方"]:
        lines.append("- 模块 **%s**" % m["标题"])
        for n in m["节点"]:
            attrs = ["空白模板 %s" % n["空白模板"]]
            if "时限" in n:
                attrs.append("时限：%s" % n["时限"])
            lines.append("  - %s（%s）" % (n["标题"], "，".join(attrs)))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="graph.py", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graph", default=DEFAULT_GRAPH, help="图文件，默认当前目录的 图.json")
    ap.add_argument("--kind", choices=("case", "preset"), default="case",
                    help="case 案件图（默认，写完重算两份视图）；preset 预设图（可写时限、无条目、不出视图）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="起手：--empty | --preset <预设图目录>")
    p.add_argument("--empty", action="store_true", help="空图")
    p.add_argument("--preset", dest="preset", help="预设图目录（或其中的 %s），整份拷入" % PRESET_FILENAME)

    sub.add_parser("validate", help="只校验，不写")
    sub.add_parser("views", help="只重算两份视图（案件图）")

    p = sub.add_parser("export-preset", help="另存：剥掉条目与不适用记录，输出一份预设图")
    p.add_argument("--out", required=True, help="个人预设图目录（落 %s），或直接给文件路径" % PRESET_FILENAME)

    p = sub.add_parser("add-module", help="新增模块")
    p.add_argument("--title", required=True)
    p.add_argument("--id", help="只对 --kind preset；案件图的 id 由引擎生成")
    p.add_argument("--before")
    p.add_argument("--after")
    p.add_argument("--first", action="store_true")
    p.add_argument("--last", action="store_true")

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

    p = sub.add_parser("add-node", help="新增节点")
    p.add_argument("--module", required=True, help="模块 id 或标题")
    p.add_argument("--title", required=True)
    p.add_argument("--id", help="只对 --kind preset；案件图的 id 由引擎生成")
    p.add_argument("--template", help="无 | <文件名>（文件住 参考/模板/ 下）")
    p.add_argument("--time-limit", help="时限一句话，只对 --kind preset")
    p.add_argument("--before")
    p.add_argument("--after")
    p.add_argument("--first", action="store_true")
    p.add_argument("--last", action="store_true")

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
    p.add_argument("--template", required=True, help="无 | <文件名>")

    p = sub.add_parser("set-time-limit", help="改时限句，只对 --kind preset")
    p.add_argument("--node", required=True)
    p.add_argument("--time-limit", help="不给即清空")

    p = sub.add_parser("generate", help="追加生成条目（来源 agent；--lawyer-written 则来源律师）")
    p.add_argument("--node", required=True)
    p.add_argument("--doc", required=True, help="文书相对路径（相对工作区根）")
    p.add_argument("--review", required=True, help="审查报告相对路径")
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
    engine = Engine(pathlib.Path(args.graph), args.kind)
    if args.cmd == "init":
        engine.init(args.empty, args.preset)
        engine.commit()
        return engine.notes
    engine.load()
    if args.cmd == "validate":
        return ["%s 合校验" % engine.graph_path.name]
    if args.cmd == "views":
        engine.require_case_kind("重算视图")
        engine.write_views()
        return ["已重算 %s 与 %s" % (VIEW_MD, VIEW_JSON)]
    if args.cmd == "export-preset":
        engine.export_preset(args.out)
        return engine.notes
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
        engine.generate(args.node, args.doc, args.review, args.lawyer_written)
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
