## What it does

`domain` 是**预设图的家**。预设图是一份构建完成、没有条目、带着空白模板的图，起手时整份拷进案件工作区。

预设图有两处，归属不同，能不能写也不同：

| 归属 | 在哪 | 谁写 | 升级时 |
| --- | --- | --- | --- |
| **出厂** | 随 skill 包分发，住包内 | 开发者经 PR | 整个被换掉；**原位读，不拷出包** |
| **个人** | 你本机 `~/.loo0ng/预设图/<名>/` | 你一句话另存 | 碰不到 |

两处不合并、同名不并存。**出厂那一份谁都不许在会话里写**，开发会话也不行。

案件工作区只记预设图的**名与归属**，路径每次按名当场解析：包一升级绝对路径就死的老毛病没有了。

## When to reach for it

不必打它的名字：

- 起手那一问「空图还是哪份预设图」：它把两组列给你看。
- 「**把这个案子的图存成预设图叫 Y**」：另存。
- 从空图建图时「**从这份指南里提节点**」：雏形。

开发者另有一条**导入**：从一个来源（目录树、指引手册、别的案件图）长出一份新的预设图，再经 PR 进仓库。这条路你用不到。

## Prerequisites

另存要当前目录是案件工作区。解析与列表随处可跑。两个 CLI 都只用 Python 标准库，跑得动 python 3.9。

## Common questions

**另存会不会改到我这个案子的图？**
不会，案件图一字不动。另存是把它剥成一份新的预设图：条目与不适用记录都剥掉，只留模块、节点、空白模板与时限，`参考/模板/` 整份拷走。

**标题里有当事人和案号，存进去不就带出去了？**
存之前它先把这些挑出来，一条一行写成「现在的标题 → 改成什么」回显给你，**你一句话之后才落**。挑不出来就说一句「标题里没有本案的东西，直接存」。

**和出厂那一份重名怎么办？**
拒，让你换个名字。两组里同名两份会让起手那一问分不清。

**「从这份指南里提节点」提出来的东西会直接进图吗？**
不会。模型先写成一份**雏形**：同名的挑掉不再提，其余列进「新提出」，末尾打出图里现有的标题清单读给你。像不像同一个由模型对着清单判、列进回显让你定；**你拍板之后才写图**，写图那一步仍经 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)。

**解析预设图时它会不会猜？**
不会。这个名与这个归属下没有就拒，不回退到另一个归属；你说的名在另一处，回显里会点出来，让你确认要哪一份。

## It's working if

- 起手那一问看见的是两组分开的列表，出厂一组、个人一组。
- 另存之后 `~/.loo0ng/预设图/<Y>/` 下有 `预设图.json` 与 `模板/`，案件图字节不变。
- 未拍板一个字不写：标题改法先回显、雏形先回显。
- 写包内那份出厂预设图无条件被拒。

## Where it fits

`domain` 只解析、列出、另存与判同名，**不直接改任何一张图**：写图一律经 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)。起手由 [setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/setup-case.md) 驱动，它调本 skill 拿列表与路径。指南与模板进工作区是归档，走 [filing](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/filing.md)；把 docx 打成文本走 [to-docx](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/to-docx.md)。出一版与拍板是 [doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md)，问在哪是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。它不含任何领域语义：换一个领域只是多一个预设图目录。
