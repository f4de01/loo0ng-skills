"""种子「兜底」：在种子「在办中」的工作区之上，收件箱里放一份律师自己写好的 DOCX。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
先跑「在办中」的回放（真的起手 CLI 加图引擎、陈述落档），再用 skill "to-docx" 的转换器
以官方模板 1-2 出一份过得了门禁的 docx，放进 收件箱/。它冒充律师自己写好的那一版：
工作台没参与写作，办节点时只归档、跑一次只披露不阻断的门禁、登记为已生成来源律师。
「在办中」的 材料/ 由那个种子的目录带着，这里照种子接口自己拷一遍。
工作区里没有任何案件内容：正文是甲乙丙占位。
"""
import importlib.util
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
SEED_DIR = pathlib.Path(__file__).resolve().parent
在办中 = SEED_DIR.parent / "在办中"
MD2DOCX = REPO / "skills" / "in-progress" / "to-docx" / "scripts" / "md2docx.py"
TEMPLATE_NAME = "1-2.关于管理人印章备案的报告.docx"
成品 = "印章备案-我自己写的.docx"

稿 = """# 关于管理人印章备案的报告

:left: 甲法院：

甲法院于甲年乙月丙日作出裁定，裁定受理乙公司破产清算一案，并指定本所担任管理人。

管理人已刻制乙公司管理人章一枚，现将印章备案如下：

| 印章名称 | 乙公司管理人章 |
|---|---|
| 印模 |  |
| 启用时间 | 甲年乙月丙日 |

特此报告

:right: 乙公司管理人
:right: （盖章）
:right: 甲年乙月丙日
"""


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

    draft = ws / "收件箱" / "稿.md"
    draft.write_text(稿, encoding="utf-8")
    r = subprocess.run([sys.executable, str(MD2DOCX), str(draft),
                        "--template", str(ws / "模板" / "官方" / TEMPLATE_NAME),
                        "--out", str(ws / "收件箱" / 成品)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    draft.unlink()
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
