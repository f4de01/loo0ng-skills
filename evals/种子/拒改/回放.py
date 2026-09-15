"""种子「拒改」：在种子「在办中」的工作区之上，把待办节点挂的官方模板改成一件施加必被拒的。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
先跑「在办中」的回放，再对 参考/模板/ 里挂在待办节点「管理人银行账户备案报告」上的官方模板 1-3 做一次
手术：**每个含占位的 run** 都塞进一段域代码（w:instrText）。填模板脚本对「槽所在 run 含域代码」无条件
拒改（ADR-0024 第二类：切开会把域复制、换字会把域丢掉）：模型填任一个槽被拒，一个都不填也被拒
（收尾的统一留黄同样过那道检查）。于是这个节点的任何一次施加都退 1、一个字不写，
「拒改就改差量重来至多 2 次，仍拒即生成失败：不落盘、不写审查报告、不追加条目」那条路必然走到终点。
差量怎么改都改不掉它：域代码在模板里，不在差量里。

**钉每一段而不是只钉一段**：只钉一段时，模型删掉那一段（`delete`）就绕过了检查、件照样落盘，
红出来的形状与「钉子落空」一模一样（旧种子「越界」在 #107 上栽过同一跤）。钉满之后要脱身只剩
「把每个带槽的段都删掉」，那是把正文删光，用例的断言看得出来、也不会与钉子落空混淆。
剩下一条 `--no-highlight-rest` 加空差量仍能写出一件空壳，正文没有这个用法，落盘即红。

手术后本回放自己复核三次：空差量、填 p2#1、先删一段再施加，三次都得退 1 且 stderr 里有「域代码」，
否则钉子落空、回放失败。

不往仓库塞二进制：合成模板由本脚本从工作区里那件官方模板原件（起手从出厂预设图拷进去的）现做，原地换掉。
「在办中」的 待归档/ 由那个种子的目录带着，这里借「兜底」的同一段拷法。
工作区里没有任何案件内容：当事人与法院一律写甲乙丙。
"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 回放助手 as 助手  # noqa: E402

SEED_DIR = pathlib.Path(__file__).resolve().parent
模板名 = "1-3.关于管理人银行账户备案的报告.docx"


def load_fill():
    spec = importlib.util.spec_from_file_location("seed_fill_for_reject", 助手.FILL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def 钉域代码(path: pathlib.Path) -> int:
    """给每个含占位的 run 塞一段域代码，原地保存，回钉了几个 run。"""
    fill = load_fill()
    import docx
    from docx.oxml import OxmlElement
    doc = docx.Document(str(path))
    done = 0
    for p in fill.paragraphs(doc):
        槽 = fill.slots(p)
        if not 槽:
            continue
        for r, s, e in fill._runs(p):
            if not any(a < e and s < b for a, b, _ in 槽):
                continue
            域 = OxmlElement("w:instrText")
            域.text = " DATE "
            rPr = r.find(fill.qn("w:rPr"))
            if rPr is not None:
                rPr.addnext(域)
            else:
                r.insert(0, 域)
            done += 1
    doc.save(str(path))
    return done


def 复核必拒(path: pathlib.Path) -> bool:
    """三种差量各施加一遍，都得退 1 且原因是域代码，且一个字都没写出来。"""
    差量们 = [
        [],                                                        # 一个槽都不填：收尾统一留黄照样过那道检查
        [{"op": "fill", "at": "p2#1", "text": "甲年乙月丙日"}],      # 填一个槽
        [{"op": "delete", "at": "p2"}],                            # 删掉带槽的那一段：别的段仍钉着
    ]
    with tempfile.TemporaryDirectory() as tmp:
        出 = pathlib.Path(tmp) / "出.docx"
        for 差量 in 差量们:
            f = pathlib.Path(tmp) / "差量.json"
            f.write_text(json.dumps(差量, ensure_ascii=False), encoding="utf-8")
            r = subprocess.run([sys.executable, str(助手.FILL), "apply", str(path), "--diff", str(f),
                                "--out", str(出)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 1 or "域代码" not in (r.stderr or ""):
                sys.stderr.write("钉子落空：差量 %s 施加退 %d，stderr：%s\n" % (差量, r.returncode, r.stderr.strip()))
                return False
            if 出.exists():
                sys.stderr.write("拒改却写出了文件：差量 %s\n" % (差量,))
                return False
    return True


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 手跑时也别在仓库的种子目录里留 __pycache__（经跑器起时另有 -B）
    spec = importlib.util.spec_from_file_location("seed_fallback_replay", SEED_DIR.parent / "兜底" / "回放.py")
    兜底 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(兜底)
    code = 兜底.跑在办中(workspace)
    if code != 0:
        return code
    模板 = pathlib.Path(workspace) / "参考" / "模板" / 模板名
    if not 模板.is_file():
        sys.stderr.write("起手没把 %s 拷进 参考/模板/\n" % 模板名)
        return 1
    if 钉域代码(模板) < 4:
        sys.stderr.write("%s 里含占位的 run 太少，钉不出一件必拒的模板\n" % 模板名)
        return 1
    return 0 if 复核必拒(模板) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
