"""种子「另存」：一个办了一半、律师自己加过一个带当事人与日期的节点的菜园案件工作区。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
先在家里造个人预设图「菜园」并整份起手，再摆出：松土已确认；律师在模块「养护」下自加了
「乙家甲年乙月丙日南墙菜畦补种记录」，出了一版并确认。这一案的构成于是比预设图多一个节点，
标题带着本案的当事人与日期，另存成预设图时要去案件化（skill "domain"）。
家取环境变量 LOO0NG_HOME（跑器每次运行另建一个临时的），没设就落在工作区里的 .预设图家/；
家的路径写进工作区根的 .家.json，用例的断言从那里读，不硬写路径。
供 skill "domain" 的用例「另存预设图」。工作区里没有任何案件内容。
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402

家文件 = ".家.json"
自加 = "乙家甲年乙月丙日南墙菜畦补种记录"
自加所在模块 = "养护"


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    home = 助手.家(ws)
    助手.造菜园(ws)
    助手.起手(ws, 助手.菜园, "个人")
    助手.办完(ws, "松土", "松土这份可以了")
    助手.引擎(ws, "add-node", "--module", 自加所在模块, "--title", 自加)
    助手.办完(ws, 自加, "补种记录这份就这样")
    基线.写基线(ws)
    # 显式 open：Path.write_text 的 newline= 是 3.10 才有的，种子要跟着引擎跑在 3.9 上（#61）
    with open(str(ws / 家文件), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"家": home.as_posix(), "预设图根": (home / 助手.PRESETS_DIRNAME).as_posix()},
                           ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
