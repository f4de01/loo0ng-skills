"""种子「兜底」：在种子「在办中」的工作区之上，待归档里放一份律师自己写好的 DOCX。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
先跑「在办中」的回放（真的起手 CLI、归档、图引擎），再用 skill "to-docx" 的填模板脚本把官方模板 1-2
的槽全填上甲乙丙，出一份没有一处黄的 docx，放进 待归档/。它冒充律师自己写好的那一版：
工作台没参与写作，办节点时只拷进节点目录、写一行「律师自写」的审查报告、登记为已生成来源律师。
「在办中」的 待归档/ 由那个种子的目录带着，这里照种子接口自己拷一遍。
工作区里没有任何案件内容：正文是甲乙丙占位。
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 回放助手 as 助手  # noqa: E402

SEED_DIR = pathlib.Path(__file__).resolve().parent
在办中 = SEED_DIR.parent / "在办中"
模板名 = "1-2.关于管理人印章备案的报告.docx"
成品 = "印章备案-我自己写的.docx"
填的字 = "甲乙丙"


def 每个槽都填(模板: pathlib.Path):
    """按填模板脚本自己认出来的槽造一份差量：一个槽一条 fill，填的都是甲乙丙。"""
    spec = importlib.util.spec_from_file_location("seed_fill", 助手.FILL)
    fill = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fill)
    import docx
    doc = docx.Document(str(模板))
    return [{"op": "fill", "at": "p%d#%d" % (i, n), "text": 填的字}
            for i, p in enumerate(fill.paragraphs(doc))
            for n, _ in enumerate(fill.slots(p), 1)]


def 跑在办中(workspace: str) -> int:
    """先摆出「在办中」：它的 待归档/ 由那个种子的目录带着，照种子接口自己拷一遍。"""
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    ws = pathlib.Path(workspace)
    shutil.copytree(str(在办中 / "待归档"), str(ws / "待归档"), dirs_exist_ok=True)
    spec = importlib.util.spec_from_file_location("seed_working_replay", 在办中 / "回放.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main(workspace)


def main(workspace: str) -> int:
    code = 跑在办中(workspace)
    if code != 0:
        return code
    ws = pathlib.Path(workspace)
    模板 = ws / "参考" / "模板" / 模板名
    with tempfile.TemporaryDirectory() as tmp:
        差量 = pathlib.Path(tmp) / "差量.json"
        差量.write_text(json.dumps(每个槽都填(模板), ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(助手.FILL), "apply", str(模板),
                            "--diff", str(差量), "--out", str(ws / "待归档" / 成品)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
