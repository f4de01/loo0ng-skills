## What it does

`filing` 把文件归进本案。来源两种，去向三格。

**来源两种**：`待归档/` 里的（**移动**），或你指的任意一个目录、包括工作区外的（**只复制，原件一字不动**）。

**去向三格**：

| 这件东西是 | 去向 |
| --- | --- |
| 本案的事实来源原件（合同、账、函、笔录、照片、压缩包） | `材料/` |
| 空白件（官方表格、格式文本，所里自己做的也算） | `参考/模板/` |
| 本案适用的官方要求文件（法院的通知、指引、材料清单） | `参考/指南/` |
| 三格都没有正向证据 | 留在待归档，回显里说一句为什么拿不准 |

**搬之前先给你一张清单**：文件、去向、一句理由；同名不同内容的与拿不准的单列一段，你一句话拍板才搬。

工作区根另有一份**归档索引**（`归档索引.md`），一行一件：路径、一句话这是什么、归档日期、文本列。出一版开场先读它，再决定读哪些原件。

## When to reach for it

不必打它的名字，在对话里说一句就行：「把那个目录整理进来」「归一下待归档」「这几份新收到的材料归档」。

另有两处由别的 skill 驱动：起手末尾清一次待归档（进起手清单，一次拍板）；出一版开场清一次待归档（**不问、不出清单**，回显一行带过）。

## Prerequisites

会话当前目录是案件工作区（有 `图.json`）。工作区外的来源目录要真在，且不能指进工作区、也不能套着工作区。脚本只用 Python 标准库，跑得动 python 3.9。

## Common questions

**同一份东西我给过两回，会搬两遍吗？**
不会。按**内容**比对，本案已有的报「已有」不搬（跨格也算），清单末尾一句「另有 N 件本案已有，不再搬」。

**同名但内容不一样的呢？**
不搬、不覆盖、不改名，留在原处，单列一段报给你：本案已有的那份是哪一件，这一件还搬不搬、搬到哪由你定。

**它会替我改文件名吗？**
永远不会。脚本没有这个参数，子目录的相对路径也原样带过去。

**压缩包和照片呢？**
原样归 `材料/`。本版不解压、不识图、不做 OCR、不转 PDF。归档索引的「文本」列因此恒为「原件」。

**我在对话里说的话会被归档成一份文件吗？**
不会。你说的事实由 [doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 一行一行追加到 `材料/律师说过的.md`，归档永不写那份文件。

**出一版的时候它为什么不问我？**
那一次是开场清场，不问、不出清单：判去向、搬、写索引一趟做完，回显一行带过。你一句话发起的整理才有确认点。

## It's working if

- 搬之前你先看见一张清单，说了那一句才动。
- 归档之后 `归档索引.md` 里每件真搬进来的都有一行；「已有」与「同名冲突」不写行。
- 工作区外的来源目录里，原件一个字节没变。
- 计划不合法或越界时**整条拒绝、一件不搬**，而不是搬一半。
- `图.json` 与两份视图一字不动。

## Where it fits

归档只搬文件，**不写图**：追加条目与改图的构成走 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)。它在起手（[setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/setup-case.md)）与出一版（[doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md)）的流程里各被调一次。归档进 `参考/模板/` 的空白件挂到哪个节点上由 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md) 记，从指南提节点是 [domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/domain.md)。问在哪、下一步做什么是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。
