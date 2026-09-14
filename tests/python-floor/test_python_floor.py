"""随包分发的脚本与种子回放跑得动 python 3.9（#61 验收）：律师那台 mac 的 /usr/bin/python3 是 3.9.6。

扫两处：`skills/*/*/scripts/*.py` 是随包分发、在律师机器上跑的七件；`evals/种子/*/回放.py` 由
`replay_seed` 用跑测试的那个解释器起，#61 的验收要求 `test_seeds.py` 在 3.9 上绿，所以种子同受
这条约束（#61 的票里漏了这一处，验收就卡在它上面）。`tests/` 与 `scripts/` 下的开发侧脚本按
ADR-0015 只在开发机上跑，不扫。

两条断言分管两类越界，都只认形状、不装全面：
- 语法：按 3.9 的 feature_version 解析，拦得住 match 之类 3.10 才有的新语法；解析期看不出来的
  （如 PEP 604 的 int | str 写在会求值的注解里）拦不住，那种得靠真在 3.9 上跑一遍。
- API：Path.write_text / read_text 的 newline= 关键字，3.10 才加，#61 就栽在这里。别的 3.10 API
  等真栽了再往这里加（ADR-0015：事故先红后绿）。

运行：python -m unittest tests/python-floor/test_python_floor.py
"""
import ast
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SHIPPED = sorted((REPO / "skills").glob("*/*/scripts/*.py"))   # skills/<bucket>/<name>/scripts/
SEEDS = sorted((REPO / "evals" / "种子").glob("*/回放.py"))
TARGETS = SHIPPED + SEEDS

METHODS_BANNING_NEWLINE_KWARG = ("write_text", "read_text")


def parse(path, feature_version=None):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path),
                     feature_version=feature_version)


class PythonFloorTest(unittest.TestCase):
    def test_finds_what_it_claims_to_scan(self):
        self.assertTrue(SHIPPED, "skills/*/*/scripts/*.py 一个都没扫到，这条断言就白站着")
        self.assertTrue(SEEDS, "evals/种子/*/回放.py 一个都没扫到，这条断言就白站着")

    def test_syntax_is_3_9(self):
        for path in TARGETS:
            with self.subTest(script=path.name):
                try:
                    parse(path, feature_version=(3, 9))
                except SyntaxError as e:
                    self.fail("%s 用了 3.9 读不懂的语法：%s" % (path.name, e))

    def test_no_newline_kwarg_on_path_text_io(self):
        for path in TARGETS:
            with self.subTest(script=path.name):
                for node in ast.walk(parse(path)):
                    if not isinstance(node, ast.Call):
                        continue
                    if not isinstance(node.func, ast.Attribute):
                        continue
                    if node.func.attr not in METHODS_BANNING_NEWLINE_KWARG:
                        continue
                    self.assertNotIn(
                        "newline", [kw.arg for kw in node.keywords],
                        "%s:%d %s(newline=) 是 3.10 才有的，改成显式 open(..., newline=) 写"
                        % (path.name, node.lineno, node.func.attr))


if __name__ == "__main__":
    unittest.main()
