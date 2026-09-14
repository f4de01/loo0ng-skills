#!/usr/bin/env python3
"""打离线兜底包：按登记清单拷 skill 目录，文本一律 LF，带 BOM 即停。标准库零依赖。

`docs/交付/现场清单.md` 段 0 P2 本来是一段手打的 bash（拷目录、剔 __pycache__、
perl 转 LF、od 验 BOM）；发布 workflow 也要拿同一个包当 Release 附件，所以收进脚本。
`docs/实测/打包.py` 有一段同样的 LF 转换，但那一个打的是 2026-09 那次 mac 实测的整包
（AGENTS.md、applescript、wheel 清单，skills 只是其中一格），是那次实测的历史产物；
两者没有合并，本脚本只管七件 skill 这一件事。
名单取自 `.claude-plugin/plugin.json` 的 skills 数组（登记清单只此一份，AGENTS.md
结构不变量 1），不在这里另抄一遍；哪天增删 skill，包跟着变。

换行符：开发机是 Windows，仓库里的 SKILL.md 是 CRLF；原样拷到 ~/.agents/skills 之后
name 字段末尾多一个 CR，Codex 认到的名字就带尾巴（2026-09-07 实测，docs/实测/打包.py）。
BOM：带 BOM 的 SKILL.md 会让 Codex 静默跳过整个根目录（#20），所以不是转掉而是停下报错。

用法：
  python scripts/pack-offline.py --zip <路径.zip>   zip 内以 skills/ 为根
  python scripts/pack-offline.py --dir <目录>       目录下每件 skill 一格，目录须不存在或为空
  两个可同时给；--root <仓库根> 默认为本脚本所在目录的上一级。
退出码：0 打好；1 名单里的目录不在、有文件带 BOM、出口目录非空；2 用法错。
"""
import argparse
import json
import pathlib
import sys
import zipfile

# 要转成 LF 的文本后缀；这之外（docx、png…）一概按二进制原样拷。
# .ps1 不在其列也不验 BOM：PowerShell 5.1 的脚本必须带 BOM（#18），skills/ 下目前也没有。
文本后缀 = {".md", ".py", ".sh", ".yaml", ".yml", ".json", ".txt"}
排除目录 = {"__pycache__", ".git"}
排除文件 = {".DS_Store"}
排除后缀 = {".pyc", ".pyo"}

BOM = bytes([0xEF, 0xBB, 0xBF])
CR = bytes([13])
LF = bytes([10])
CRLF = CR + LF


class 打不了(Exception):
    pass


def 登记的名单(根):
    """[(skill 名, 仓库内目录)]：plugin.json 里的路径是 ./skills/<bucket>/<name>（Matt 分桶），
    名字取最后一段；包内仍平铺成 skills/<name>/，律师机上 ~/.agents/skills/ 认的是名字不是桶。"""
    清单 = json.loads((根 / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return [(p.rstrip("/").rsplit("/", 1)[-1], 根 / p.rstrip("/").lstrip("./")) for p in 清单["skills"]]


def 是文本(f):
    # .gitattributes 没有后缀，单认文件名
    return f.suffix.lower() in 文本后缀 or f.name == ".gitattributes"


def 收条目(根, 名单):
    """列出要进包的文件，相对路径以 <skill 名>/ 开头；名单里的目录缺一件就整个不打。"""
    缺 = [n for n, 底 in 名单 if not 底.is_dir()]
    if 缺:
        raise 打不了("登记清单上的 " + "、".join(缺) + " 在 plugin.json 指的路径下找不到")
    条目 = []
    for n, 底 in 名单:
        for f in sorted(底.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(底)
            if any(part in 排除目录 for part in rel.parts[:-1]):
                continue
            if f.name in 排除文件 or f.suffix.lower() in 排除后缀:
                continue
            条目.append((n + "/" + rel.as_posix(), f))
    return 条目


def 读一件(f):
    """返回 (字节, 改没改行尾)；带 BOM 的文本文件抛 打不了。"""
    原 = f.read_bytes()
    if not 是文本(f):
        return 原, False
    if 原.startswith(BOM):
        raise 打不了("BOM")
    换 = 原.replace(CRLF, LF).replace(CR, LF)
    return 换, 换 != 原


def 写目录(出, 内容):
    for rel, data in 内容:
        p = 出 / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


def 写zip(出, 内容):
    出.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(出, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, data in 内容:
            # 时间戳写死，同一份源打两次字节相同
            info = zipfile.ZipInfo("skills/" + rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zip", dest="zip路径", default=None, help="输出 zip，内以 skills/ 为根")
    ap.add_argument("--dir", dest="目录", default=None, help="输出目录，每件 skill 一格")
    ap.add_argument("--root", default=None, help="仓库根，默认为脚本所在目录的上一级")
    args = ap.parse_args(argv)
    if not args.zip路径 and not args.目录:
        ap.error("至少给一个出口：--zip 或 --dir")

    根 = pathlib.Path(args.root) if args.root else pathlib.Path(__file__).resolve().parents[1]
    try:
        名单 = 登记的名单(根)
        条目 = 收条目(根, 名单)
    except 打不了 as e:
        print(str(e), file=sys.stderr)
        return 1

    内容 = []
    带BOM = []
    转了 = 0
    for rel, f in 条目:
        try:
            data, 改了 = 读一件(f)
        except 打不了:
            带BOM.append(rel)
            continue
        转了 += 1 if 改了 else 0
        内容.append((rel, data))
    if 带BOM:
        for rel in 带BOM:
            print("带 BOM，装到 Codex 那边会被静默跳过：skills/" + rel, file=sys.stderr)
        return 1

    目录 = pathlib.Path(args.目录) if args.目录 else None
    if 目录 is not None and 目录.exists():
        if not 目录.is_dir():
            print(str(目录) + " 不是目录，先删掉或换一个", file=sys.stderr)
            return 1
        if any(目录.iterdir()):
            print(str(目录) + " 非空，先删掉或换一个", file=sys.stderr)
            return 1
    z = pathlib.Path(args.zip路径) if args.zip路径 else None
    if z is not None and z.exists():
        # 与 --dir 一条口径：两个出口都不覆盖已有的东西
        print(str(z) + " 已经在了，先删掉或换一个", file=sys.stderr)
        return 1

    if 目录 is not None:
        目录.mkdir(parents=True, exist_ok=True)
        写目录(目录, 内容)
        print("打好 " + str(目录) + "：" + str(len(名单)) + " 件 skill，" + str(len(内容)) + " 个文件")
    if z is not None:
        写zip(z, 内容)
        print("打好 " + str(z) + "：" + str(len(名单)) + " 件 skill，" + str(len(内容)) + " 个文件，"
              + str(z.stat().st_size // 1024) + " KB")
    print("行尾转成 LF 的有 " + str(转了) + " 个文件；名单取自 .claude-plugin/plugin.json：" + "、".join(n for n, _ in 名单))
    return 0


if __name__ == "__main__":
    sys.exit(main())
