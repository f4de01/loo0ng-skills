"""种子「图引擎」：用合成小领域整份起手一个测试工作区。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
走真的起手 CLI（skill "setup-case"，#31 落地）：六格、图与两份视图、工作区指针块
（ADR-0009 机制 B）都由它落，引擎一改、起手一改，用这个种子的用例立刻红。
工作区里没有任何案件内容。
"""
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
SETUP = REPO / "skills" / "engineering" / "setup-case" / "scripts" / "setup.py"
DOMAIN_DIR = REPO / "evals" / "领域" / "菜园"


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    r = subprocess.run([sys.executable, str(SETUP), "init", "--full", "--domain", str(DOMAIN_DIR),
                        "--workspace", str(ws)], cwd=str(ws),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
