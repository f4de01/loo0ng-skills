"""回答的形状与「只读」这两条（#19 验收 2、3、4）。

路由没有脚本，它的行为全在正文里；能机械守住的是形状与边界：
    第一行是待拍板行，后面固定五段，样例照这个形状写（验收 3）
    决策树只从案件图的视图算，四问，不提预设图（验收 2）
    只读：没有 scripts/，正文点名图与两份视图一个字节不变（验收 4）
真跑一遍再比字节要有模型在场，那是 eval 的事（#11：doit 与 ask-loo0ng 没有脚本，靠毕业时的 eval）。
运行：python -m unittest discover -s tests/ask-loo0ng -p 'test_*.py'
"""
import re
import unittest

from support import SKILL_DIR, 一节, 正文

五段 = ("## 你在哪", "## 三问", "## 往下的路", "## 相近入口分界线", "## 下一句该打什么")
待拍板行起头 = "待拍板："
怎么答标题 = "## 我读什么、怎么答"


def 样例():
    """正文里那份 markdown 样例回复。"""
    m = re.search(r"```markdown\n(.*?)\n```", 正文(), re.S)
    assert m, "正文里的样例回复不见了"
    return m.group(1)


class 待拍板行Test(unittest.TestCase):
    """回答第一行列出高亮已清、还没确认的节点，并给出下一句该打什么（验收 3）。"""

    def test_样例第一行就是待拍板行(self):
        self.assertTrue(样例().splitlines()[0].startswith(待拍板行起头),
                        "样例回复的第一行不是待拍板行：%r" % 样例().splitlines()[0])

    def test_待拍板行带着下一句该打什么(self):
        self.assertIn("/doit 确认 ", 样例().splitlines()[0], "待拍板行没给出下一句该打的那一串")

    def test_正文写明一个都没有时怎么写(self):
        self.assertIn("待拍板：无", 一节("## 回复长什么样"), "一个都没有时那一行怎么写，正文没写")

    def test_正文写明读不到视图时怎么写(self):
        self.assertIn("待拍板：无法判断", 一节("## 回复长什么样"), "视图不在时那一行怎么写，正文没写")

    def test_正文说明它读的是高亮已清且未确认(self):
        节 = 一节("## 回复长什么样") + 一节(怎么答标题)
        for 词 in ("已清", "未确认"):
            self.assertIn(词, 节, "正文没说清待拍板行取的是哪些节点：缺「%s」" % 词)


class 五段Test(unittest.TestCase):
    def test_样例里五段按序齐全(self):
        位置 = [样例().find(h) for h in 五段]
        for h, i in zip(五段, 位置):
            self.assertNotEqual(i, -1, "样例里缺一段：%s" % h)
        self.assertEqual(位置, sorted(位置), "样例里五段的顺序乱了")

    def test_正文把五段写成硬形状(self):
        节 = 一节("## 回复长什么样")
        for h in 五段:
            self.assertIn("`%s`" % h, 节, "正文没把「%s」写成固定小标题" % h)


class 决策树Test(unittest.TestCase):
    """只读案件图的前方，不引用任何预设图（验收 2）。"""

    def test_四问(self):
        self.assertIn("四问有序决策树", 一节(怎么答标题), "决策树的问数没改成四问")

    def test_命中问的编号只到四(self):
        节 = 一节(怎么答标题) + 一节("## 回复长什么样")
        for n in re.findall(r"命中问 (\d)", 节):
            self.assertIn(n, tuple("1234"), "出现了「命中问 %s」，树上没有这一问" % n)

    def test_树读的是视图里的前方(self):
        节 = 一节(怎么答标题)
        self.assertIn("图视图.json", 节, "决策树没写明读哪一份")
        self.assertIn("前方", 节, "决策树没用视图里算好的前方")

    def test_前方是模块数组取到节点那一层(self):
        问3 = [l for l in 一节(怎么答标题).splitlines() if l.startswith("3. `前方`")]
        self.assertEqual(len(问3), 1, "决策树里问 3 那一行不见了或多出一行")
        for 词 in ("模块", "节点"):
            self.assertIn(词, 问3[0], "问 3 没说清前方是模块数组、要取到节点那一层"
                                      "（skill \"graph\" 的 GRAPH-FORMAT.md）")

    def test_答这几问那一节不提预设图(self):
        self.assertNotIn("预设图", 一节(怎么答标题), "答三问时引用了预设图：案件图自足（ADR-0023）")

    def test_时限从视图取不去别处找(self):
        节 = 一节(怎么答标题)
        self.assertIn("时限", 节, "查时限那一步没了")
        self.assertNotIn("AGENTS.md", 节, "又去 AGENTS.md 找路径了：时限随起手拷进案件图（ADR-0023）")


class 只读Test(unittest.TestCase):
    """回答前后图与视图一个字节不变（验收 4）。"""

    def test_没有脚本目录(self):
        self.assertFalse((SKILL_DIR / "scripts").exists(), "路由长出了 scripts/：它只读，没有写盘的东西")

    def test_正文点名三份文件都不变(self):
        节 = 一节("## 不做的事")
        for f in ("图.json", "图视图.md", "图视图.json"):
            self.assertIn(f, 节, "「不做的事」里没点名 %s" % f)
        self.assertIn("一个字节", 节, "「一个字节都不变」这句没了")

    def test_正文写明不触发不写图(self):
        文 = 正文()
        for 句 in ("不触发", "不写图"):
            self.assertIn(句, 文, "正文缺「%s」" % 句)

    def test_正文写明入口都存在与以对方SKILL为准(self):
        文 = 正文()
        self.assertIn("即使它们不在你看到的 skill 列表里", 文)
        self.assertRegex(文, r"以.{0,10}`SKILL\.md`.{0,10}为准")


if __name__ == "__main__":
    unittest.main()
