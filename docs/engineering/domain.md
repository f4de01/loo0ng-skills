## What it does

`domain` 是**预设图的家**。预设图是一份构建完成、没有条目、带着空白模板的图，起手时整份拷进案件工作区。

它按**出厂与个人两种归属**管理预设图，案件工作区只记名与归属，每次使用时再解析路径。

## When to reach for it

模型会在需要列出、解析或另存预设图，以及从指南提节点时调用它，你不用记名字：

- 起手那一问「空图还是哪份预设图」：它把两组列给你看。
- 「**把这个案子的图存成预设图叫 Y**」：另存。
- 从空图建图时「**从这份指南里提节点**」：雏形。

开发者另有一条**导入**：从一个来源（目录树、指引手册、别的案件图）长出一份新的预设图，再经 PR 进仓库。这条路你用不到。

## 两处两归属

预设图有两处，归属决定它随谁保存、升级时会怎样：

| 归属 | 在哪 | 怎么形成 | 升级时 |
| --- | --- | --- | --- |
| **出厂** | 随 skill 包分发，住包内 | 开发者导入后经 PR 进包 | 整个被换掉 |
| **个人** | 你本机 `~/.loo0ng/预设图/<名>/` | 你从案件图另存，或开发者导入 | 保留在本机，不受包升级影响 |

**出厂件谁都不许在会话里写**，开发会话也一样。起手直接读取包内那份，把图整份拷进案件工作区；个人另存则把可复用的构成留在包外。两处不合并，同名不并存，因此另存时碰到出厂名或已有目标都会拒绝，需要换名。

另存需要一份已有的案件图。它剥掉办案条目与不适用记录，连同空白模板保存为新的个人预设图；标题中属于本案的信息先列出改法，等你拍板后再另存并修改新图。案件图上的记录与标题保持原样，下一个案子起手时可以选这份个人预设图。

## 按名解析，不存路径

列表和解析随处可用。工作区记下的是例如「归属：个人，名：Y」这样的指针；真正使用时，模型让 `domain` 找到它此刻所在的目录。包升级可能换掉安装目录，**名与归属**仍是查找依据，工作区不必追着安装路径改。

归属也是查找条件。指定归属里找不到就拒绝，即使另一处有这个名字，也只提示你确认，不自动换用。起手之后，案件图已有自己的整份构成；预设图后来变了，案件图不会自动跟着增加节点。

## Common questions

**活图、出厂种子、回流和入库去哪了？**
这套机制已退场，`home`、`intake`、`from-case` 都已删除。现在只有出厂与个人两类预设图：律师说「把这个案子的图存成预设图叫 Y」保存可复用构成；开发者从来源导入个人预设图，再经 PR 进仓库成为出厂件。出处：[CHANGELOG 0.6.0，domain 重做](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

**另存会带走本案记录，或改掉当前案件图吗？**
案件图不动。新预设图剥掉全部条目与不适用记录，只留模块、节点、空白模板与时限，另把 `参考/模板/` 整份拷走。标题中的本案信息先列出改法，等你一句话才落；不是把案件材料整包存成预设。出处：[CHANGELOG 0.6.0，新增另存](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

**升级会把我存的预设图换掉吗？同名又怎么办？**
个人件住本机 `~/.loo0ng/预设图/`，升级碰不到；出厂件随包整体更新，会话里谁都不能写。另存与出厂重名会拒，已有个人目标也不覆盖。工作区只记名与归属，使用时再解析路径；指定归属下找不到就拒，不自动换用另一处。出处：[CHANGELOG 0.6.0，两处两归属与按名解析](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

**原来的 `docx-text` 怎么用？**
它已搬到 `to-docx`，对应 `fill.py list --plain`，把 DOCX 打成不带槽和高亮标记的纯文本，供整读指南或文书。出处：[CHANGELOG 0.6.0，docx-text 搬家](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

## It's working if

- 起手那一问看见的是两组分开的列表，出厂一组、个人一组。
- 另存之后 `~/.loo0ng/预设图/<Y>/` 下有 `预设图.json` 与 `模板/`，案件图字节不变。
- 未拍板一个字不写：标题改法先回显、雏形先回显。
- 写包内那份出厂预设图无条件被拒。

## Where it fits

`domain` 只解析、列出、另存与判同名，**不直接改任何一张图**：写图一律经 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)。起手由 [setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/setup-case.md) 驱动，它调本 skill 拿列表与路径。指南与模板进工作区是归档，走 [filing](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/filing.md)；把 docx 打成文本走 [to-docx](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/to-docx.md)。出一版与拍板是 [doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md)，问在哪是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。它不含任何领域语义：换一个领域只是多一个预设图目录。
