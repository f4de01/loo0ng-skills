## What it does

`setup-case` 把当前目录长成一个案件工作区，一案一次。它只问你一件事：**空图，还是用哪一份预设图起**（随包出厂的与你自己存下的分两组列给你）。你选了之后一条命令落下全部东西：

```
<案件工作区>/
├── 图.json  图视图.md  图视图.json  AGENTS.md  CLAUDE.md
├── 待归档/                   ← 你原本堆在这个目录里的东西都在这里
├── 材料/
├── 参考/模板/  参考/指南/
└── 文书/                     ← <模块>/<节点>/ 出件时才建
```

选了预设图，它的模块、节点、空白模板文件名与时限句一次拷进案件图，`模板/` 整份拷进 `参考/模板/`。之后这张图**自足**：接下来该办什么只从它自己算，不再回头看预设图。

工作区根的 `AGENTS.md` 只记四项：预设图的名与归属、图与视图的文件名、入口名、「本工作区对 skill 仓库只读」。**一条路径都不记**——记下来，skill 包一升级那条路径就死了。

## When to reach for it

在一个新案子的目录里打 `/setup-case`，一次。**目录里已经堆着文件不妨**：它们一律当作待归档，由起手挪进 `待归档/`，该归到哪是下一步的事。

已经有 `图.json` 的目录它会拒绝：那个目录已经是案件工作区，要改图的构成在对话里说一句（走 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)），要另起一案换一个目录。

## Prerequisites

当前目录没有 `图.json`。脚本只用 Python 标准库，跑得动 python 3.9。

## Common questions

**它会问我几个问题？**
一个：空图还是哪份预设图。你那句话里已经说了的（「起手，用破产那份」）它不再问一遍。之后全程只有一个确认点——末尾那张**起手清单**。

**起手清单是什么？**
三张表合成一张：哪些文件要归到哪一格、哪些是你起手前就写好的成品要登记到某个节点、哪些同名冲突或拿不准。你一句话拍板整张（「都按建议来」「第 3 条不要」「4 归材料」），说了才搬、才写图。没有文件要归时连这张清单都没有。

**我起手前已经写好的文书怎么办？**
对得上图上某个节点的，起手会建议登记为那个节点的**已生成**（来源记你，审查报告只有「律师自写」一行）。登记不是确认：要确认，在办那个节点的对话里说一句。对不上任何节点的就是普通材料，照常归 `材料/`。

**没有预设图可选怎么办？**
两组都空就是这次只能从空图起手。空图起手不拷模板，`参考/模板/` 先空着，你自己的空白件之后说一句话归档进来。

**我想把这一案的图留给下一案。**
办完之后说一句「把这个案子的图存成预设图叫 Y」，走 [domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/domain.md)。起手不负责这件事。

## It's working if

- 六格目录、`图.json` 与两份视图一次落齐，你原本堆在目录里的东西都在 `待归档/`。
- 收尾第一段是固定五行：目录与图、起手图、待归档、归档、既有成品，件数逐个写实。
- `AGENTS.md` 里只有名与归属，翻遍找不到一条路径。
- 没有任何节点被自动确认。

## Where it fits

起手是主线第 1 步，跑完就交给 [doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 办第一个节点。它自己不出件、不确认：清待归档调 [filing](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/filing.md)，预设图的列表与路径调 [domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/domain.md)，写图经 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)。不知道下一步做什么就打 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。
