"""种子「兜底」：在种子「在办中」的工作区之上，收件箱里放一份律师自己写好的 DOCX。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
先跑「在办中」的回放（真的起手 CLI 加图引擎、陈述落档），再用 skill "to-docx" 的填模板脚本
把官方模板 1-2 的槽全填上甲乙丙，出一份过得了门禁的 docx，放进 收件箱/。它冒充律师自己写好的那一版：
工作台没参与写作，办节点时只归档、跑一次只披露不阻断的门禁、登记为已生成来源律师。
「在办中」的 材料/ 由那个种子的目录带着，这里照种子接口自己拷一遍。
工作区里没有任何案件内容：正文是甲乙丙占位。
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
SEED_DIR = pathlib.Path(__file__).resolve().parent
在办中 = SEED_DIR.parent / "在办中"
FILL = REPO / "skills" / "in-progress" / "to-docx" / "scripts" / "fill.py"
TEMPLATE_NAME = "1-2.关于管理人印章备案的报告.docx"
成品 = "印章备案-我自己写的.docx"

填的字 = "甲乙丙"


def 每个槽都填(模板: pathlib.Path):
    """按填模板脚本自己认出来的槽造一份差量：一个槽一条 fill，填的都是甲乙丙。"""
    spec = importlib.util.spec_from_file_location("seed_fill", FILL)
    fill = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fill)
    import docx
    doc = docx.Document(str(模板))
    return [{"op": "fill", "at": "p%d#%d" % (i, n), "text": 填的字}
            for i, p in enumerate(fill.paragraphs(doc))
            for n, _ in enumerate(fill.slots(p), 1)]


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    ws = pathlib.Path(workspace)

    # 跑器按种子接口把 <种子>/ 下的条目原样拷进工作区；本种子借「在办中」的材料，自己拷一遍。
    shutil.copytree(在办中 / "材料", ws / "材料", dirs_exist_ok=True)

    spec = importlib.util.spec_from_file_location("seed_working_replay", 在办中 / "回放.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main(workspace)
    if code != 0:
        return code

    模板 = ws / "模板" / "官方" / TEMPLATE_NAME
    差量 = ws / "收件箱" / "差量.json"
    差量.write_text(json.dumps(每个槽都填(模板), ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(FILL), "apply", str(模板),
                        "--diff", str(差量), "--out", str(ws / "收件箱" / 成品)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    差量.unlink()
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
